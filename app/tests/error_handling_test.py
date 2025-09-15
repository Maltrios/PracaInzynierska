import time
from datetime import timedelta

import pytest
import os

import io

from models.temp_file_model import TempFile
from tests.conftest import TestingSessionLocal, override_get_db
from tests.test_api import logged_in_user
from utils.auth import create_access_token
from celery_app.tasks import analyse_data




def test_crated_existed_user(client):
    response = client.post("/auth/register", json={"email": "user@example.com", "password": "Password1!"})
    token = response.json()
    assert response.status_code == 400, response.json == {"detail":"Email already registered"}

def test_created_user_with_password_validation_error(client):
    response = client.post("/auth/register", json={"email": "user@example.com", "password": "password"})
    token = response.json()
    assert response.status_code == 422
    error_detail = response.json()["detail"][0]
    assert error_detail["loc"] == ["body", "password"]
    assert "Password must contain at least one digit" in error_detail["msg"]
    assert "Password must contain at least one uppercase letter" in error_detail["msg"]
    assert "Password must contain at least one special character" in error_detail["msg"]

def test_logging_out_a_logged_out_user(client):
    response = client.post("/auth/login", json={"email": "user@example.com", "password": "password"})
    token = response.json()
    print(response.json())
    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token['access_token']}"})
    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 200, response.json == {"detail": "User was already logged out"}

def test_upload_buggy_file_at_least_20_rows(client, logged_in_user):
    token, _ = logged_in_user

    file_path = os.path.join(os.path.dirname(__file__), "..", "csvFile", "bug_20_rows.csv")
    file_path = os.path.abspath(file_path)
    with open(file_path, "rb") as f:
        response = client.post(
            "/file/upload-csv/show_column",
            files={"file": ("bug_20_rows.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Dataset must have at least 20 rows."}

def test_upload_buggy_file_not_found_target_column(client, logged_in_user, db = next(override_get_db())):
    token, _ = logged_in_user

    file_path = os.path.join(os.path.dirname(__file__), "..", "csvFile", "bug_2_samples.csv")
    file_path = os.path.abspath(file_path)
    with open(file_path, "rb") as f:
        response_file = client.post(
            "/file/upload-csv/show_column",
            files={"file": ("bug_2_samples.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    file_id = response_file.json()["file_id"]
    file = db.query(TempFile).filter(TempFile.user_id == 1, TempFile.id == file_id).first()

    assert file is not None

    tmp_path = file.tmp_path
    original_filename = file.original_filename

    with pytest.raises(ValueError, match="Selected column not found in dataset"):
        analyse_data.run(
            file_id=file.id,
            tmp_path=tmp_path,
            target_column="Buggy",
            save_file=True,
            user_id=1,
            original_filename=original_filename,
            type_search=True
        )


def test_upload_buggy_file_target_column_with_1_sample(client, logged_in_user, db = next(override_get_db())):
    token, _ = logged_in_user

    file_path = os.path.join(os.path.dirname(__file__), "..", "csvFile", "bug_2_samples.csv")
    file_path = os.path.abspath(file_path)
    with open(file_path, "rb") as f:
        response_file = client.post(
            "/file/upload-csv/show_column",
            files={"file": ("bug_2_samples.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    file_id = response_file.json()["file_id"]
    file = db.query(TempFile).filter(TempFile.user_id == 1, TempFile.id == file_id).first()

    assert file is not None

    tmp_path = file.tmp_path
    original_filename = file.original_filename

    with pytest.raises(ValueError, match="Each class in target must have at least 2 samples."):
        analyse_data.run(
            file_id=file.id,
            tmp_path=tmp_path,
            target_column="target_buggy",
            save_file=True,
            user_id=1,
            original_filename=original_filename,
            type_search=True
        )

def test_upload_buggy_file_target_column_with_2_unique_classes(client, logged_in_user, db = next(override_get_db())):
    token, _ = logged_in_user

    file_path = os.path.join(os.path.dirname(__file__), "..", "csvFile", "bug_2_column.csv")
    file_path = os.path.abspath(file_path)
    with open(file_path, "rb") as f:
        response_file = client.post(
            "/file/upload-csv/show_column",
            files={"file": ("bug_2_column.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    file_id = response_file.json()["file_id"]
    file = db.query(TempFile).filter(TempFile.user_id == 1, TempFile.id == file_id).first()
    assert file is not None

    tmp_path = file.tmp_path
    original_filename = file.original_filename

    with pytest.raises(ValueError, match="Target column must have at least 2 unique classes."):
        analyse_data.run(
            file_id=file.id,
            tmp_path=tmp_path,
            target_column="target_buggy",
            save_file=True,
            user_id=1,
            original_filename=original_filename,
            type_search=True
        )


def test_upload_empty_file(client, logged_in_user):
    token, _ = logged_in_user

    fake_file = io.BytesIO(b"")
    response_file = client.post(
        "/file/upload-csv/show_column",
        files={"file": ("NotFoundError.csv", fake_file, "text/csv")},
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert response_file.status_code == 400
    assert response_file.json()["detail"] == "Uploaded file is empty"

def test_upload_no_file(client, logged_in_user):
    token, _ = logged_in_user

    response = client.post(
        "/file/upload-csv/show_column",
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Field required"

def test_generate_tree_with_bad_json_request(client, logged_in_user, db = next(override_get_db())):
    token, _ = logged_in_user

    file_path = os.path.join(os.path.dirname(__file__), "..", "csvFile", "drug200.csv")
    file_path = os.path.abspath(file_path)
    with open(file_path, "rb") as f:
        response_file = client.post(
            "/file/upload-csv/show_column",
            files={"file": ("drug200.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    response = client.post(
        "/file/start-analysis",
        json={
            "target_column": "Drug",
            "file_id": response_file.json()["file_id"],
            "type_search": 4,
            "save_file": 4
        },
        headers={"Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == 422
    print(response.json())
    assert (response.json()["detail"][0]["msg"] and response.json()["detail"][1]["msg"]
            == "Input should be a valid boolean, unable to interpret input")

def test_not_authorization(client):
    response = client.get("/user/me")
    assert response.status_code ==  403
    assert response.json()["detail"] == "Not authenticated"

def test_invalid_token(client):
    response = client.get("/user/me",
                          headers={"Authorization": f"Bearer invalidToken"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

def test_upload_invalid_file_format(client, logged_in_user):
    token, _ = logged_in_user
    fake_txt = io.BytesIO(b"txt file")
    response = client.post(
        "/file/upload-csv/show_column",
        files={"file": ("wrong_format.txt", fake_txt, "text/plain")},
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail":"The file must be in CSV format."}

def test_csv_file_without_column_name(client, logged_in_user):
    token, _ = logged_in_user

    file_path = os.path.join(os.path.dirname(__file__), "..", "csvFile", "bug_no_column_name.csv")
    file_path = os.path.abspath(file_path)
    with open(file_path, "rb") as f:
        response = client.post(
            "/file/upload-csv/show_column",
            files={"file": ("bug_no_column_name.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    assert response.status_code == 400
    assert response.json() == {'detail': 'The CSV file must contain valid column names in the first row.'}

def test_expired_access_token_allows_refresh(client,logged_in_user):
    token, _ = logged_in_user
    access_token = create_access_token(
        {"sub": str(1)},
        timedelta(seconds=1),
    )

    time.sleep(2)

    response = client.get(
        "/user/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 401
    refresh_token = token["refresh_token"]

    response_refresh = client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
    assert response_refresh.status_code == 200
    assert response_refresh.json()["access_token"] != access_token
