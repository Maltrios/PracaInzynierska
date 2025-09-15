import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base
import os

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE")


db = sa.create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=db, autocommit=False, autoflush=False, expire_on_commit=False)

Base = declarative_base()

def get_db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()