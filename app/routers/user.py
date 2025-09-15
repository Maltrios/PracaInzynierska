from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from dependencies import get_current_user
from database import get_db
from models.user_model import User
from schemas.user_schama import UserResponse, UserUpdate, MessageResponse

router = APIRouter()

@router.get("/me",response_model=UserResponse,
            summary="Displaying user information",
            description="""  
                            Allows you to display the ID, email, activity, account creation 
                            date and last login of the logged-in user 
                        """,
            responses={
                401: {"description": "Not authenticated"}
            })
def get_current_user(user: User = Depends(get_current_user)):
    return user

@router.patch("/update", response_model=UserResponse,
              summary="Returns updated user data",
              description="""  
                            Allows you to display the ID, email, activity, 
                            account creation date and last login of the logged-in user whose data has been edited.
                          """,
              responses={
                  401: {"description": "Not authenticated"},
                  409: {"description": "Email already registered"},
                  422: {"description": "Password does not meet the requirements"}
              }
              )
def update_profile(update_data: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if update_data.email:
        existing_user = db.query(User).filter(func.lower(User.email) == func.lower(update_data.email)).first()

        if existing_user and existing_user.id != user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user.email = update_data.email

    if update_data.password:
        from utils.auth import hash_password
        user.password_hash = hash_password(update_data.password)

    db.commit()
    db.refresh(user)
    return user

@router.delete("/delete", response_model=MessageResponse,
               summary="Deleting a user account",
               description="""  
                           Allows you to delete a user account from the database, this step is irreversible.
                         """,
               responses={
                  401: {"description": "Not authenticated"}
              }
)
def delete_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}