import os
from uuid import uuid4

from dependencies import oauth2_scheme
from fastapi import APIRouter, Depends, HTTPException, status
from models.Blacklisted_tokens_model import BlacklistedToken
from models.refresh_token_model import RefreshToken

from schemas.user_schama import UserCreate, UserLogin, UserResponse, Token
from models.user_model import User
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from starlette.responses import JSONResponse
from utils.auth import hash_password, verify_password, create_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt, ExpiredSignatureError


router = APIRouter()
refresh_scheme = HTTPBearer()

@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(func.lower(User.email) == func.lower(user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        password_hash=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created"}


@router.post("/login", response_model=Token)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(func.lower(User.email) == func.lower(user.email)).first()

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    db_user.last_login = datetime.now(timezone.utc)
    db.commit()

    session_jti = str(uuid4())

    token = create_access_token({"sub": str(db_user.id), "jti": session_jti})
    refresh_token_str = create_access_token({"sub": str(db_user.id), "jti": session_jti},expires_delta=timedelta(days=7))

    db_refresh_token = RefreshToken(
        user_id = db_user.id,
        token = refresh_token_str,
        jti=session_jti,
        expires_at = datetime.now() + timedelta(days=7),
    )
    db.add(db_refresh_token)
    db.commit()
    db.refresh(db_refresh_token)

    return {"access_token": token, "refresh_token": refresh_token_str, "token_type": "bearer"}

@router.post("/refresh")
def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(refresh_scheme),db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    db_token = db.query(RefreshToken).filter(RefreshToken.token == token, RefreshToken.revoked == False,
                                             RefreshToken.expires_at > datetime.now()).first()

    if not db_token:
        raise HTTPException(status_code=400, detail="Refresh token revoked or expired")

    new_access_token = create_access_token({"sub": str(user_id)})
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    access_token = credentials.credentials

    try:
        decoded_payload = jwt.decode(access_token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
    except ExpiredSignatureError:
        return JSONResponse(status_code=400, content={"detail": "Token has already expired"})
    except JWTError:
        return JSONResponse(status_code=400, content={"detail": "Token is invalid or already revoked"})

    expires_at = datetime.fromtimestamp(decoded_payload.get("exp"), tz=timezone.utc)
    jti = decoded_payload.get("jti")

    db_blacklist = BlacklistedToken(
        token=access_token,
        expires_at=expires_at
    )
    try:
        db.add(db_blacklist)
        db.commit()
    except IntegrityError:
        db.rollback()
        return JSONResponse(status_code=409, content={"detail": "User was already logged out"})

    user_id = decoded_payload.get("sub")
    db.query(RefreshToken).filter(RefreshToken.jti == jti, RefreshToken.user_id == user_id).delete()

    db.commit()
    return JSONResponse(status_code=200, content={"detail": "Logged out successfully"})

