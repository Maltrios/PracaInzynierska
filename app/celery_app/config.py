import os

import redis
from celery import Celery
from database import Base, db
from dotenv import load_dotenv

from models import Blacklisted_tokens_model, file_model, refresh_token_model, temp_file_model, user_model, user_action
Base.metadata.create_all(bind=db)

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

celery_app = Celery(
    "task",
    broker=REDIS_URL,
    backend=REDIS_URL
)

r = redis.from_url(REDIS_URL)

celery_app.autodiscover_tasks(['celery_app.tasks'])