from fastapi import Header

from app.db import hash_owner_token

# FastAPI maps the parameter name to the "X-Owner-Token" header automatically (underscores -> hyphens).
# The raw token is a client-generated opaque value (never a real identity); only its hash is stored.


def require_owner(x_owner_token: str = Header(..., min_length=1, max_length=200)) -> str:
    return hash_owner_token(x_owner_token)


def optional_owner(x_owner_token: str | None = Header(None, max_length=200)) -> str | None:
    return hash_owner_token(x_owner_token) if x_owner_token else None
