from fastapi import FastAPI
from routers import auth, user, file, ws
from models import Blacklisted_tokens_model, file_model, refresh_token_model, temp_file_model, user_model, user_action
from dotenv import load_dotenv
load_dotenv()
from database import Base, db

Base.metadata.create_all(bind=db)

app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(file.router, prefix="/file", tags=["Files"])
app.include_router(ws.router, tags=["WebSocket"])

@app.get("/")
def read_root():
    return "Server is running"