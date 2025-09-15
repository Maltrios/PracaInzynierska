import os
from uuid import uuid4

from dependencies import oauth2_scheme
from fastapi import APIRouter, Depends, HTTPException, status
from models.Blacklisted_tokens_model import BlacklistedToken
from models.refresh_token_model import RefreshToken

from schemas.user_schama import UserCreate, UserLogin, AccessToken, RefreshTokenSchema, MessageResponse
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

@router.post("/register", summary="new user registration", response_model=MessageResponse,
             description=
             """
                Creates a new user based on the data provided. The email address must be unique, 
                and the password is stored in hashed form.
             """,
             responses={
                 400: {"description": "Email already registered"},
                 422: {"description": "password does not meet the requirements"},
                 201: {"description": "User created"},
             },
             status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(func.lower(User.email) == func.lower(user.email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = User(
        email=user.email,
        password_hash=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"detail": "User created"}


@router.post("/login", response_model=AccessToken, summary="User login to account",
             description="""
                User logs into the account with email and password.
                Returns JWT access token, refresh token, and token type (bearer).
             """,
             responses={
                 400: {"description": "Invalid email or password"}
             })
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(func.lower(User.email) == func.lower(user.email)).first()

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password")

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

@router.post("/refresh", response_model=RefreshTokenSchema,
             summary="Refreshes expired JWT tokens",
             description="""
                             Refreshes expired JWT tokens and returns a new access token along with the token type.
                          """,
             responses={
                 401: {"description": "Invalid or expired refresh token",
                        "content": {
                           "application/json": {
                               "examples": {
                                   "invalid": {"value": {"detail": "Invalid refresh token"}},
                                   "expired": {"value": {"detail": "Refresh token expired"}},
                                   "revoked_or_expired": {"value": {"detail": "Refresh token revoked or expired"}}
                               }
                           }
                       }
                       },
                 200: {"description": "Token refreshed successfully",
                       "content":{
                           "application/json": {
                               "example": {
                                    "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
                                    "token_type": "bearer"
                               }
                           }
                       }}
             })
def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(refresh_scheme),db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    db_token = db.query(RefreshToken).filter(RefreshToken.token == token, RefreshToken.revoked == False,
                                             RefreshToken.expires_at > datetime.now()).first()

    if not db_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

    new_access_token = create_access_token({"sub": str(user_id)})
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/logout",
             response_model=MessageResponse,
             summary="Logging out of your user account",
             description="""
                            Used to log the user out of the account and block the active JWT token
                          """,
             responses={
                 401: {"description": "Token has already expired",
                       "content": {
                           "application/json": {
                               "examples": {
                                   "invalid": {"value": {"detail": "Token is invalid"}},
                                   "expired": {"value": {"detail": "Token has already expired"}},
                               }
                           }
                       }
                       },
                 200: {"description": "User logged out successfully",
                       "content": {
                           "application/json": {
                               "examples": {
                                   "logout": {"value": {"detail": "User logged out successfully"}},
                                    "already_logged_out": {"value": {"detail": "User already logged out"}}
                               }}
                       }
                       }
             })
def logout(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    access_token = credentials.credentials

    try:
        decoded_payload = jwt.decode(access_token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
    except ExpiredSignatureError:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Token has already expired"})
    except JWTError:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Token is invalid"})

    expires_at = datetime.fromtimestamp(decoded_payload.get("exp"), tz=timezone.utc)
    jti = decoded_payload.get("jti")
    user_id = decoded_payload.get("sub")
    existing = db.query(BlacklistedToken).filter(BlacklistedToken.token == access_token).first()
    if existing:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "User already logged out"})

    db_blacklist = BlacklistedToken(
        token=access_token,
        expires_at=expires_at
    )

    db.add(db_blacklist)
    db.query(RefreshToken).filter(RefreshToken.jti == jti, RefreshToken.user_id == user_id).delete()
    db.commit()

    return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "User logged out successfully"})

