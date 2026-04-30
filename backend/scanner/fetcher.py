"""
Fetches repository files from GitHub using PyGithub.
Applies smart filtering: skips binaries, test files, node_modules, etc.
Prioritizes security-critical folders.
"""
import base64
from github import Github, GithubException

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "coverage", "vendor", "migrations"
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff",
    ".woff2", ".ttf", ".eot", ".pdf", ".zip", ".tar", ".gz",
    ".map", ".lock", ".min.js", ".min.css"
}

SKIP_PATTERNS = {
    ".env", ".env.local", ".env.production", ".DS_Store"
}

TEST_PATTERNS = {"test", "spec", "__tests__", "__mocks__", "fixtures"}

PRIORITY_DIRS = [
    "src/", "app/", "lib/", "api/", "auth/", "payment/",
    "security/", "middleware/", "routes/", "controllers/"
]

MAX_FILE_SIZE_BYTES = 500_000  # 500KB
MAX_FILES = 200


def _should_skip(path: str) -> bool:
    """Return True if this file should be excluded from scanning."""
    parts = path.lower().split("/")

    # Skip hidden/build/dependency dirs
    for part in parts[:-1]:
        if part in SKIP_DIRS or part.startswith("."):
            return True

    filename = parts[-1]
    # Skip env and config files
    if filename in SKIP_PATTERNS:
        return True

    # Skip test files
    for pattern in TEST_PATTERNS:
        if pattern in filename.lower():
            return True

    # Skip binary/minified extensions
    for ext in SKIP_EXTENSIONS:
        if filename.endswith(ext):
            return True

    return False


def _priority_score(path: str) -> int:
    """Higher score = scanned first."""
    for i, prefix in enumerate(PRIORITY_DIRS):
        if path.startswith(prefix):
            return len(PRIORITY_DIRS) - i
    return 0


def fetch_repo_files(repo_full_name: str, token: str) -> list[dict]:
    """
    Fetches up to MAX_FILES source files from the GitHub repo.
    Returns a list of dicts: {path, content, size}
    """
    g = Github(token)
    repo = g.get_repo(repo_full_name)

    # Collect all file paths via the git tree (faster than recursive get_contents)
    try:
        tree = repo.get_git_tree(sha=repo.default_branch, recursive=True)
    except GithubException:
        tree = repo.get_git_tree(sha="main", recursive=True)

    all_files = []
    for item in tree.tree:
        if item.type != "blob":
            continue
        if _should_skip(item.path):
            continue
        if item.size and item.size > MAX_FILE_SIZE_BYTES:
            continue
        all_files.append(item)

    # Sort by priority
    all_files.sort(key=lambda x: _priority_score(x.path), reverse=True)
    all_files = all_files[:MAX_FILES]

    # Fetch content
    fetched = []
    for item in all_files:
        try:
            content_file = repo.get_contents(item.path)
            if content_file.encoding == "base64":
                content = base64.b64decode(content_file.content).decode("utf-8", errors="replace")
            else:
                content = content_file.decoded_content.decode("utf-8", errors="replace")

            fetched.append({
                "path": item.path,
                "content": content,
                "size": item.size or 0,
            })
        except Exception:
            # Skip files that fail to decode (true binaries)
            continue

    return fetched
