"""
Gemini Code Quality Analyzer.
Chunks files by function/class boundaries (max 150 lines per chunk),
sends batches of 5 to Gemini 2.5 Flash, parses strict JSON responses.
"""
import os
import re
import json
import asyncio
import uuid
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

SYSTEM_PROMPT = (
    "You are an expert code security and quality reviewer for a software team. "
    "Analyze code and return ONLY valid JSON. No markdown. No explanation outside JSON."
)

USER_PROMPT_TEMPLATE = """Analyze this code chunk from file {file_path}:

{code_chunk}

Return JSON exactly in this format:
{{
  "issues": [
    {{
      "severity": "critical|warning|suggestion",
      "category": "security|bug|quality|performance",
      "line_start": <number>,
      "line_end": <number>,
      "title": "<max 10 words>",
      "explanation": "<2-3 sentences, specific to this code>",
      "suggested_fix": "<corrected code snippet only>",
      "confidence": <0.0-1.0>
    }}
  ]
}}

Focus on: security vulnerabilities, unhandled exceptions, logic errors, performance bottlenecks, hardcoded values.
If no issues found, return {{"issues": []}}"""


def _chunk_by_boundaries(content: str, max_lines: int = 150) -> list[str]:
    """
    Split code into chunks at function/class definition boundaries.
    Falls back to hard line count if no boundaries found.
    """
    lines = content.split("\n")
    if len(lines) <= max_lines:
        return [content]

    boundary_patterns = re.compile(
        r"^(def |async def |class |function |const \w+ = \(|export default |module\.exports)",
        re.MULTILINE
    )

    chunks = []
    current_chunk_start = 0

    for i, line in enumerate(lines):
        if i > 0 and boundary_patterns.match(line):
            if i - current_chunk_start >= max_lines:
                chunks.append("\n".join(lines[current_chunk_start:i]))
                current_chunk_start = i

    # Add remaining lines
    remaining = "\n".join(lines[current_chunk_start:])
    if remaining.strip():
        chunks.append(remaining)

    return chunks if chunks else [content]


def _extract_json(text: str) -> dict:
    """Extract JSON from Gemini response, handling markdown fences."""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    # Find the first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON found in response: {text[:200]}")


async def _analyze_chunk(model, file_path: str, chunk: str, chunk_offset: int) -> list[dict]:
    """Send a single chunk to Gemini and parse the response."""
    prompt = USER_PROMPT_TEMPLATE.format(file_path=file_path, code_chunk=chunk)
    try:
        response = await model.generate_content_async(
            [{"role": "user", "parts": [prompt]}],
            generation_config={"temperature": 0.1}
        )
        data = _extract_json(response.text)
        issues = data.get("issues", [])

        normalized = []
        for issue in issues:
            normalized.append({
                "id": str(uuid.uuid4()),
                "severity": issue.get("severity", "suggestion"),
                "category": issue.get("category", "quality"),
                "file_path": file_path,
                "line_start": issue.get("line_start", 1) + chunk_offset,
                "line_end": issue.get("line_end", 1) + chunk_offset,
                "title": str(issue.get("title", "Code Issue"))[:100],
                "explanation": issue.get("explanation", ""),
                "suggested_fix": issue.get("suggested_fix", ""),
                "confidence": float(issue.get("confidence", 0.7)),
                "source": "gemini",
            })
        return normalized

    except Exception as e:
        print(f"[Gemini] Error analyzing {file_path}: {e}")
        return []


async def _analyze_file(model, file: dict) -> list[dict]:
    """Chunk a single file and gather Gemini results for all chunks."""
    chunks = _chunk_by_boundaries(file["content"])
    all_findings = []
    offset = 0

    for chunk in chunks:
        findings = await _analyze_chunk(model, file["path"], chunk, offset)
        all_findings.extend(findings)
        offset += chunk.count("\n") + 1

    return all_findings


async def analyze_with_gemini(files: list[dict]) -> list[dict]:
    """
    Main entry point.
    Processes files in batches of 5 with a 1-second delay between batches
    to stay within Gemini rate limits.
    """
    if not os.getenv("GEMINI_API_KEY"):
        print("[Gemini] No API key — skipping Gemini analysis.")
        return []

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    all_findings = []
    batch_size = 5

    for i in range(0, len(files), batch_size):
        batch = files[i: i + batch_size]
        tasks = [_analyze_file(model, f) for f in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_findings.extend(result)
            # Silently skip exceptions from individual files

        if i + batch_size < len(files):
            await asyncio.sleep(1)  # Rate limit protection

    return all_findings
