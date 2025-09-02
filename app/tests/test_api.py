from datetime import timezone, datetime

import pytest
import os


def test_create_user(client):
    response = client.post(
        "/auth/register", json={
              "email": "test@example.com",
              "password": "string"
            }
        )
    assert response.status_code == 200, response.text

@pytest.fixture()
def logged_in_user(client):
    response = client.post("/auth/login", json={"email": "user@example.com", "password": "password"})
    token = response.json()

    def logout():
        client.post("/auth/logout", headers={"Authorization": f"Bearer {token['access_token']}"})

    yield token, logout



@pytest.mark.parametrize("logout_before", [False, True])
def test_get_user_info(logged_in_user, logout_before,client):
    token, logout = logged_in_user

    if logout_before:
        logout()

    response = client.get(
        "/user/me",
        headers={"Authorization": f"Bearer {token["access_token"]}"}
    )

    if logout_before:
        assert response.status_code == 400
        assert response.json()["detail"] == "Token has been revoked, please login again"
    else:
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == 1
        assert data["email"] == "user@example.com"
        assert data["is_active"] == True


@pytest.mark.parametrize("logout_before", [False, True])
def test_user_update(logged_in_user, logout_before, client):
    token, logout = logged_in_user

    if logout_before:
        logout()

    response = client.patch(
        "/user/update",
        json={
            "email": "updated_user@example.com",
            "password": "updated_password"
        },
        headers={"Authorization": f"Bearer {token["access_token"]}"}
    )

    if logout_before:
        assert response.status_code == 400
        assert response.json()["detail"] == "Token has been revoked, please login again"
    else:
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == 1
        assert data["email"] == "updated_user@example.com"


@pytest.mark.parametrize("logout_before", [False, True])
def test_refresh_token(logged_in_user, logout_before, client):
    token, logout = logged_in_user

    if logout_before:
        logout()

    response = client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {token["refresh_token"]}"}
    )

    if logout_before:
        assert response.status_code == 400
        assert response.json() == {"detail": "Refresh token revoked or expired"}
    else:
        assert response.status_code == 200, response.text

@pytest.mark.parametrize("logout_before", [False, True])
def test_delete_user(logged_in_user, logout_before, client):
    token, logout = logged_in_user

    if logout_before:
        logout()

    response = client.delete(
        "/user/delete",
        headers={"Authorization": f"Bearer {token["access_token"]}"}
    )

    if logout_before:
        assert response.status_code == 400
        assert response.json()["detail"] == "Token has been revoked, please login again"
    else:
        assert response.status_code == 200
        assert response.json() =={"message": "User deleted"}


@pytest.mark.parametrize("logout_before", [False, True])
def test_upload_csv_file_show_target_column(logged_in_user, logout_before, client):
    token, logout = logged_in_user

    if logout_before:
        logout()

    file_path = os.path.join(os.path.dirname(__file__), "..", "csvFile", "drug200.csv")
    file_path = os.path.abspath(file_path)

    with open(file_path, "rb") as f:
        response = client.post(
            "/file/upload-csv/show_column",
            files={"file": ("drug200.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    if logout_before:
        assert response.status_code == 400
        assert response.json() == {"detail": "Token has been revoked, please login again"}
    else:
        assert response.status_code == 200
        assert response.json() == {
              "columns": [
                "Age",
                "Sex",
                "BP",
                "Cholesterol",
                "Na_to_K",
                "Drug"
              ],
            "file_id": 1
            }

@pytest.fixture
def uploaded_file_id(logged_in_user, client):
    token, _ = logged_in_user
    file_path = os.path.join(os.path.dirname(__file__), "..", "csvFile", "drug200.csv")
    file_path = os.path.abspath(file_path)

    with open(file_path, "rb") as f:
        resp = client.post(
            "/file/upload-csv/show_column",
            files={"file": ("drug200.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )
    return resp.json()["file_id"]

@pytest.mark.parametrize("logout_before", [False, True])
def test_select_decision_column_and_generate_tree(logged_in_user, logout_before, uploaded_file_id, client):
    token, logout = logged_in_user

    if logout_before:
        logout()

    response = client.post(
        "/file/upload-csv/set_target_column",
        json={
          "target_column": "Drug",
          "file_id": uploaded_file_id,
          "type_search": True,
          "save_file": True
        },
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )

    if logout_before:
        assert response.status_code == 400
        assert response.json() == {"detail": "Token has been revoked, please login again"}
    else:
        assert response.status_code == 200
        expected_prefix = "iVBORw0KGgoAAAANSUhEUgAA"
        assert response.json()["image_base64"].startswith(expected_prefix)

@pytest.fixture
def prepare_test_show_and_download_files(logged_in_user, uploaded_file_id,client):
    token, logout = logged_in_user

    response = client.post(
        "/file/upload-csv/set_target_column",
        json={
            "target_column": "Drug",
            "file_id": uploaded_file_id,
            "type_search": True,
            "save_file": True
        },
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )


    assert response.status_code == 200
    data = response.json()

    return {
        "logout": logout,
        "token": token,
        "file_id": uploaded_file_id,
        "response_data": data
    }

@pytest.mark.parametrize("logout_before", [False, True])
def test_show_user_file(logout_before,prepare_test_show_and_download_files, client):

    token = prepare_test_show_and_download_files["token"]
    file_id = prepare_test_show_and_download_files["file_id"]
    logout = prepare_test_show_and_download_files["logout"]
    if logout_before:
        logout()

    response = client.get(
            "/file/get_file/files",
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    if logout_before:
        assert response.status_code == 400
        assert response.json() == {"detail": "Token has been revoked, please login again"}
    else:
        assert response.status_code == 200
        data = response.json()[0]
        assert data["id"] == file_id
        assert data["filename"] == "drug200.csv"
        assert data["size_bytes"] == 6027
        uploaded_at = datetime.fromisoformat(data["uploaded_at"])
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
        assert abs((uploaded_at - datetime.now(timezone.utc)).total_seconds()) < 60

@pytest.mark.parametrize("logout_before", [False, True])
def test_download_user_file(logout_before,prepare_test_show_and_download_files, client):
    token = prepare_test_show_and_download_files["token"]
    file_id = prepare_test_show_and_download_files["file_id"]
    logout = prepare_test_show_and_download_files["logout"]
    if logout_before:
        logout()

    response = client.get(
            f"/file/get_file/file/download/{file_id}",
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )

    if logout_before:
        assert response.status_code == 400
        assert response.json() == {"detail": "Token has been revoked, please login again"}
    else:
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "attachment" in response.headers["content-disposition"]
        assert "drug200.csv" in response.headers["content-disposition"]


