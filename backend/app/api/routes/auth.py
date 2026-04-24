"""Authentication helper routes.

Firebase Auth registration and login should happen in the frontend with the
Firebase client SDK. The backend validates Firebase ID tokens on protected routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user

router = APIRouter()


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "data": {
            "uid": current_user["uid"],
            "authProvider": current_user.get("authProvider", "firebase"),
        }
    }


@router.post("/register")
async def register():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use Firebase Auth client SDK to register users.",
    )


@router.post("/login")
async def login():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use Firebase Auth client SDK to sign in and send the ID token to this API.",
    )


@router.post("/logout")
async def logout():
    return {"data": {"loggedOut": True}}
