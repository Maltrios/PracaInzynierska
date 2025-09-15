from database import SessionLocal
from models.user_model import User
from passlib.handlers.bcrypt import bcrypt
from sqlalchemy.exc import IntegrityError
from models.refresh_token_model import RefreshToken
import pandas as pd

file = pd.read_csv("user_data.csv")

for index, row in file.iterrows():
    session = SessionLocal()

    created_at = pd.to_datetime(row.created_at, dayfirst=True)
    last_login = pd.to_datetime(row.last_login, dayfirst=True)
    try:
        new_user = User(
            email=row.email,
            password_hash=bcrypt.hash(row.password),
            created_at=created_at.strftime("%Y/%m/%d"),
            last_login=last_login.strftime("%Y/%m/%d"),
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
    except IntegrityError:
        session.rollback()
        print("A user with this email already exists!")
    finally:
        session.close()


