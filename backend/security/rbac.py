"""Role‑based access control utilities.

Provides a ``require_role`` dependency that can be applied to any FastAPI
endpoint. If the current user does not have one of the allowed roles, an
``HTTPException`` with status 403 is raised.
"""

from __future__ import annotations

from typing import List

from fastapi import Depends, HTTPException, status

from .auth import SimpleUser, get_current_user


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Operation not permitted"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_role(allowed_roles: List[str]):
    def role_checker(user: SimpleUser = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise AuthorizationError(f"User role '{user.role}' not allowed for this operation")
        return user
    return role_checker
