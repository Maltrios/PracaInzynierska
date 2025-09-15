import string

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional


def password_validator(value: str) -> str:
    errors = []
    if len(value) < 8:
       errors.append("Password must be at least 8 characters long")
    if not any(char.isdigit() for char in value):
        errors.append("Password must contain at least one digit")
    if not any(char.isupper() for char in value):
        errors.append("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in value):
        errors.append("Password must contain at least one lowercase letter")
    if not any(char in string.punctuation for char in value):
        errors.append("Password must contain at least one special character")

    if errors:
        raise ValueError("; ".join(errors))
    return value



class UserCreate(BaseModel):
    email: EmailStr = Field(..., example="user@example.com", description="Unique email of the user")
    password: str = Field(..., example="Password1!", description="Password for the user account")

    _validate_password = field_validator("password")(password_validator)

class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="user@example.com", description="Unique email of the user")
    password: str = Field(..., example="Password1!", description="Password for the user account")

class UserResponse(BaseModel):
    id: int = Field(..., example=1, description="User identification number")
    email: EmailStr = Field(..., example="user@example.com", description="User's email address")
    is_active: bool = Field(..., example=True,
                            description="checking whether the user account is active and can generate trees")

    created_at: datetime = Field(..., example="2025-09-03T12:34:56Z",
                                 description="Date of creation of the user account")

    last_login: Optional[datetime] = Field(example="2025-09-03T12:34:56Z",
                                           description="Date of the user's last login")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

    _validate_password = field_validator("password")(password_validator)

class AccessToken(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR", description="JWT access token")
    refresh_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR", description="JWT refresh token")
    token_type: str = Field(..., example="Bearer", description="Type of the token")

class RefreshTokenSchema(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR", description="JWT access token")
    token_type: str = Field(..., example="Bearer", description="Type of the token")

class TargetColumnRequest(BaseModel):
    target_column: str = Field(..., example="example",
                               description="The column in the dataset that will be used as the decision target")

    file_id: int = Field(..., example=1, description="file identification number")

    type_search: bool = Field(..., example=True,
                              description="The value determines how the model should be trained, "
                                          "whether it should randomly select values or check each"
                                          "one in turn and choose the best one.")

    save_file: bool = Field(..., example=True,
                            description="A value that specifies whether the file should be saved on the server disk.")

class MessageResponse(BaseModel):
    detail: str = Field(..., example="Operation completed successfully",
                        description="Message displayed after the command has been successfully executed ")
    class Config:
        from_attributes = True