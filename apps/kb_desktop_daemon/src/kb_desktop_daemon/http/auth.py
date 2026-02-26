from fastapi import HTTPException, Request, status


async def require_auth(request: Request) -> None:
    token = request.app.state.ctx.auth_token
    header = request.headers.get("Authorization", "")
    if header != f"Bearer {token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
