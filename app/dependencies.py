import os

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from models.Blacklisted_tokens_model import BlacklistedToken
from sqlalchemy.orm import Session
from database import get_db
from models.user_model import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

oauth2_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    db_blacklisted_tokens = db.query(BlacklistedToken).filter(token == BlacklistedToken.token).first()

    if db_blacklisted_tokens:
        raise HTTPException(status_code=400, detail="Token has been revoked, please login again")

    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user
