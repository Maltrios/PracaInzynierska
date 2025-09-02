from unittest.mock import patch
from unittest.mock import Mock
from fastapi.testclient import TestClient
from database import get_db
from passlib.handlers.bcrypt import bcrypt
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from models.user_model import *
import pytest
from main import app
import routers.file

DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(DATABASE_URL,
                       connect_args={
                           "check_same_thread": False,
                       },
                       poolclass=StaticPool)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def disable_go_service(monkeypatch):
    monkeypatch.setattr(routers.file, "send_action", Mock(return_value="patched-OK"))
    yield

def override_get_db():
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    db_user = User(email="user@example.com", password_hash=bcrypt.hash("password"))
    session.add(db_user)
    session.commit()
    session.close()

    yield
    Base.metadata.drop_all(bind=engine)
