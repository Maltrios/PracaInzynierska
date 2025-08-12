from fastapi import APIRouter, Depends
from fastapi.params import Depends
from sqlalchemy.orm import Session
from dependencies import get_current_user
from database import get_db
from models.user_model import User
from schemas.user_schama import UserResponse, UserUpdate

router = APIRouter()

@router.get("/me",response_model=UserResponse)
def get_current_user(user: User = Depends(get_current_user)):
    return user

@router.patch("/update", response_model=UserResponse)
def update_profile(update_data: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if update_data.email:
        user.email = update_data.email
    if update_data.password:
        from utils.auth import hash_password
        user.password_hash = hash_password(update_data.password)

    db.commit()
    db.refresh(user)
    return user

@router.delete("/delete")
def delete_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}