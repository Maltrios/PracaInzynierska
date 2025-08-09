from fastapi import APIRouter, Depends, HTTPException, status
from schemas.user_schama import UserCreate, UserLogin, UserResponse, Token
from models.user_model import User
from sqlalchemy.orm import Session
from database import get_db
from datetime import datetime
from sqlalchemy import func
from utils.auth import hash_password, verify_password, create_access_token

router = APIRouter()

@router.post("/register", response_model=Token)
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

    token = create_access_token({"sub": str(new_user.id)})

    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(func.lower(User.email) == func.lower(user.email)).first()

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    db_user.last_login = datetime.now()
    db.commit()

    token = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}
