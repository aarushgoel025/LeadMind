import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
GITHUB_SCOPE = "repo,read:user,user:email"


@router.get("/github")
def github_login():
    """Redirect user to GitHub OAuth authorization page."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(500, "GITHUB_CLIENT_ID not configured")

    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&scope={GITHUB_SCOPE}"
        f"&redirect_uri={BACKEND_URL}/auth/callback"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/callback")
async def github_callback(code: str, request: Request):
    """
    GitHub sends back a `code`. We exchange it for an access_token,
    store the token in the server-side session, and redirect to dashboard.
    """
    if not code:
        raise HTTPException(400, "No code returned from GitHub")

    # Exchange code for access_token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        error = token_data.get("error_description", "Unknown error")
        return RedirectResponse(url=f"{FRONTEND_URL}/?error={error}")

    # Fetch basic user info to store in session
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
    user_data = user_response.json()

    # Store in session — token is NEVER sent to the frontend
    request.session["access_token"] = access_token
    request.session["user"] = {
        "login": user_data.get("login"),
        "name": user_data.get("name", user_data.get("login")),
        "avatar_url": user_data.get("avatar_url"),
        "email": user_data.get("email"),
    }

    return RedirectResponse(url=f"{FRONTEND_URL}/dashboard")


@router.get("/me")
def get_current_user(request: Request):
    """Return current logged-in user info from session."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


@router.post("/logout")
def logout(request: Request):
    """Clear the session."""
    request.session.clear()
    return {"message": "Logged out successfully"}


def require_auth(request: Request) -> dict:
    """
    FastAPI dependency. Use in any route that requires login:
      current_user: dict = Depends(require_auth)
    """
    user = request.session.get("user")
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {
        **user,
        "token": request.session.get("access_token"),
    }
