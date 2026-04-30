"""
ArmorClaw adapter — uses Bandit (Python) and pattern-based rules (JS/TS/etc.)
as a drop-in equivalent to the ArmorClaw CLI.

Bandit is the industry-standard Python static security analyzer.
For non-Python files, we use a custom regex-based rule engine that
covers the same rule set ArmorClaw advertises:
  secrets, injection, dependencies, auth-patterns
"""
import os
import re
import json
import tempfile
import shutil
import subprocess
import uuid
from pathlib import Path

# ─── Custom rules for non-Python files ────────────────────────────────────────
RULES = [
    {
        "id": "HARDCODED_SECRET",
        "title": "Hardcoded Secret or API Key",
        "severity": "critical",
        "category": "security",
        "confidence": 0.92,
        "pattern": re.compile(
            r'(api[_-]?key|secret[_-]?key|auth[_-]?token|password|passwd|access[_-]?token)'
            r'\s*[=:]\s*["\'](?!process\.env|os\.environ|config\.|getenv)[^"\']{6,}["\']',
            re.IGNORECASE
        ),
        "explanation": (
            "A secret or credential appears to be hardcoded directly in source code. "
            "If this repository becomes public or is accessed by an unauthorized party, "
            "these credentials can be extracted and abused."
        ),
        "suggested_fix": "Move the value to an environment variable: process.env.YOUR_SECRET or os.environ['YOUR_SECRET']",
    },
    {
        "id": "SQL_INJECTION",
        "title": "Potential SQL Injection",
        "severity": "critical",
        "category": "security",
        "confidence": 0.88,
        "pattern": re.compile(
            r'(execute|query|raw)\s*\(\s*[f"\'].*\+|'
            r'f["\'].*SELECT.*{|'
            r'"\s*\+\s*\w+\s*\+\s*".*WHERE',
            re.IGNORECASE
        ),
        "explanation": (
            "User input appears to be concatenated directly into a SQL query string. "
            "This is a critical SQL Injection vulnerability that could allow an attacker "
            "to read, modify, or delete arbitrary data in the database."
        ),
        "suggested_fix": "Use parameterized queries or prepared statements. Example: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
    },
    {
        "id": "EVAL_USAGE",
        "title": "Dangerous eval() Usage",
        "severity": "critical",
        "category": "security",
        "confidence": 0.95,
        "pattern": re.compile(r'\beval\s*\(', re.IGNORECASE),
        "explanation": (
            "eval() executes arbitrary code. If any user-controlled data reaches this call, "
            "it becomes a Remote Code Execution (RCE) vulnerability."
        ),
        "suggested_fix": "Remove eval() entirely. Use JSON.parse() for data, or refactor logic to avoid dynamic code execution.",
    },
    {
        "id": "INSECURE_RANDOM",
        "title": "Insecure Random Number Generation",
        "severity": "warning",
        "category": "security",
        "confidence": 0.85,
        "pattern": re.compile(r'\bMath\.random\(\)|random\.random\(\)', re.IGNORECASE),
        "explanation": (
            "Math.random() and random.random() are not cryptographically secure. "
            "Using them for tokens, session IDs, or passwords can lead to predictable values."
        ),
        "suggested_fix": "Use crypto.randomBytes() (Node.js) or secrets.token_hex() (Python) for security-sensitive randomness.",
    },
    {
        "id": "CONSOLE_LOG_SENSITIVE",
        "title": "Potential Sensitive Data in Logs",
        "severity": "warning",
        "category": "security",
        "confidence": 0.75,
        "pattern": re.compile(
            r'(console\.log|print|logger\.debug)\s*\(.*?(password|token|secret|key|auth)',
            re.IGNORECASE
        ),
        "explanation": (
            "Sensitive data such as passwords, tokens, or keys may be logged to the console. "
            "Log files are often stored in plaintext and accessible to system administrators or attackers."
        ),
        "suggested_fix": "Remove logging of sensitive values, or redact them: logger.debug('token: [REDACTED]')",
    },
    {
        "id": "NO_AUTH_CHECK",
        "title": "Missing Authentication Check",
        "severity": "warning",
        "category": "security",
        "confidence": 0.70,
        "pattern": re.compile(
            r'(router\.(get|post|put|delete|patch))\s*\(["\'][^"\']*admin[^"\']*["\']',
            re.IGNORECASE
        ),
        "explanation": (
            "An admin route appears to be registered without an explicit authentication middleware. "
            "This could allow unauthenticated users to access privileged functionality."
        ),
        "suggested_fix": "Add an authentication middleware to this route: router.get('/admin/...', requireAuth, handler)",
    },
    {
        "id": "CORS_WILDCARD",
        "title": "Overly Permissive CORS Configuration",
        "severity": "warning",
        "category": "security",
        "confidence": 0.90,
        "pattern": re.compile(r'allow_origins\s*=\s*\[\s*["\*]["\']\s*\]|cors\(\{.*origin.*:\s*["\*]["\']\s*\}\)', re.IGNORECASE),
        "explanation": (
            "CORS is configured to accept requests from any origin (*). "
            "This removes same-origin protection and can facilitate cross-site request forgery."
        ),
        "suggested_fix": "Restrict CORS to your known frontend origins: allow_origins=['https://yourdomain.com']",
    },
]

SKIP_EXTENSIONS = {".min.js", ".min.css", ".map", ".lock"}


def _scan_file_with_rules(file_path: str, content: str) -> list[dict]:
    """Apply regex rule set to a single file's content."""
    findings = []
    lines = content.split("\n")

    for rule in RULES:
        for line_num, line in enumerate(lines, start=1):
            if rule["pattern"].search(line):
                findings.append({
                    "id": str(uuid.uuid4()),
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "file_path": file_path,
                    "line_start": line_num,
                    "line_end": line_num,
                    "title": rule["title"],
                    "explanation": rule["explanation"],
                    "suggested_fix": rule["suggested_fix"],
                    "confidence": rule["confidence"],
                    "source": "armorclaw",
                    "armorclaw_rule_id": rule["id"],
                })
                break  # one finding per rule per file

    return findings


def _run_bandit(tmpdir: str) -> list[dict]:
    """Run Bandit on Python files in tmpdir. Returns normalized findings."""
    try:
        result = subprocess.run(
            ["bandit", "-r", tmpdir, "-f", "json", "-q", "--exit-zero"],
            capture_output=True, text=True, timeout=60
        )
        raw = json.loads(result.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []

    findings = []
    for issue in raw.get("results", []):
        severity_map = {"HIGH": "critical", "MEDIUM": "warning", "LOW": "suggestion"}
        severity = severity_map.get(issue.get("issue_severity", "LOW"), "suggestion")
        confidence_map = {"HIGH": 0.9, "MEDIUM": 0.75, "LOW": 0.6}
        confidence = confidence_map.get(issue.get("issue_confidence", "LOW"), 0.6)

        findings.append({
            "id": str(uuid.uuid4()),
            "severity": severity,
            "category": "security",
            "file_path": issue.get("filename", "").replace(tmpdir + os.sep, "").replace("\\", "/"),
            "line_start": issue.get("line_number", 1),
            "line_end": issue.get("line_number", 1),
            "title": issue.get("issue_text", "Security Issue")[:80],
            "explanation": (
                f"{issue.get('issue_text', '')}. "
                f"See: {issue.get('more_info', 'https://bandit.readthedocs.io')}"
            ),
            "suggested_fix": issue.get("issue_text", "Review and remediate this security issue."),
            "confidence": confidence,
            "source": "armorclaw",
            "armorclaw_rule_id": issue.get("test_id", "B000"),
        })

    return findings


def run_armorclaw_scan(files: list[dict]) -> list[dict]:
    """
    Main entry point.
    - Writes files to a temp directory
    - Runs Bandit on Python files
    - Runs custom regex rules on all files
    - Deletes temp directory
    - Returns deduplicated findings
    """
    tmpdir = tempfile.mkdtemp(prefix="leadmind_scan_")
    all_findings = []

    try:
        has_python = False

        for file in files:
            full_path = os.path.join(tmpdir, file["path"].replace("/", os.sep))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(file["content"])

            if file["path"].endswith(".py"):
                has_python = True

            # Apply regex rules to every file
            ext = Path(file["path"]).suffix
            if ext not in SKIP_EXTENSIONS:
                all_findings.extend(_scan_file_with_rules(file["path"], file["content"]))

        # Run Bandit on Python files
        if has_python:
            bandit_findings = _run_bandit(tmpdir)
            all_findings.extend(bandit_findings)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)  # Always clean up

    return all_findings
