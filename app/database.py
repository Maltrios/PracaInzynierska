import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base
import os

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE")


db = sa.create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=db, autocommit=False, autoflush=False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()