from fastapi import APIRouter, Request, Depends, HTTPException
from github import Github
from routers.auth import require_auth

router = APIRouter(prefix="/repos", tags=["repos"])


@router.get("")
def list_repos(current_user: dict = Depends(require_auth)):
    """
    Fetch the authenticated user's GitHub repos via PyGithub.
    Returns name, language, open_issues_count, and clone_url.
    """
    token = current_user.get("token")
    if not token:
        raise HTTPException(401, "No GitHub token in session")

    g = Github(token)
    user = g.get_user()

    repos = []
    for repo in user.get_repos(sort="updated", type="owner"):
        if repo.fork:
            continue  # skip forks for cleaner list

        repos.append({
            "id": repo.id,
            "name": repo.name,
            "fullName": repo.full_name,
            "description": repo.description or "",
            "language": repo.language or "Unknown",
            "url": repo.html_url,
            "cloneUrl": repo.clone_url,
            "openIssuesCount": repo.open_issues_count,
            "private": repo.private,
            "lastPushedAt": repo.pushed_at.isoformat() if repo.pushed_at else None,
            "stars": repo.stargazers_count,
        })

        if len(repos) >= 30:  # cap at 30 repos
            break

    return repos
