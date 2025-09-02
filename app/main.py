from fastapi import FastAPI
from routers import auth, user, file
from models import *
from dotenv import load_dotenv
load_dotenv()
from database import Base, db

# Base.metadata.create_all(bind=db)

app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(file.router, prefix="/file", tags=["Files"])

@app.get("/")
def read_root():
    return "Server is running"