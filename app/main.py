from fastapi import FastAPI
from routers import auth, user, file
import models.user_model
from dotenv import load_dotenv
load_dotenv()


app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(file.router, prefix="/file", tags=["Files"])

