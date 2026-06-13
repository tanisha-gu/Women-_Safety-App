"""
Auth routes: /api/auth/register, /login, /profile, /update-profile
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from auth_utils import create_access_token, get_current_user_id, hash_password, verify_password
from store import store

router = APIRouter()
# ─── Schemas ──────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str
class LoginRequest(BaseModel):
    email: str
    password: str
class UpdateProfileRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
# ─── Helpers ──────────────────────────────────────────────────────────────────
def _public_user(user: dict) -> dict:
    """Strip password hash before returning."""
    return {k: v for k, v in user.items() if k != "password_hash"}
# ─── Routes ───────────────────────────────────────────────────────────────────
@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    # Check duplicate email
    for u in store["users"].values():
        if u["email"] == body.email:
            raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "name": body.name,
        "email": body.email,
        "phone": body.phone,
        "password_hash": hash_password(body.password),
        "emergency_contacts": [],
        "safe_zones": [],
        "created_at": datetime.utcnow().isoformat(),
    }
    store["users"][user_id] = user
    token = create_access_token(user_id)
    return {"success": True, "token": token, "user": _public_user(user)}


@router.post("/login")
async def login(body: LoginRequest):
    user = next((u for u in store["users"].values() if u["email"] == body.email), None)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user["id"])
    return {"success": True, "token": token, "user": _public_user(user)}


@router.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user_id)):
    user = store["users"].get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _public_user(user)


@router.patch("/update-profile")
async def update_profile(body: UpdateProfileRequest, user_id: str = Depends(get_current_user_id)):
    user = store["users"].get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.name:
        user["name"] = body.name
    if body.phone:
        user["phone"] = body.phone
    store["users"][user_id] = user
    return {"success": True, "user": _public_user(user)}
