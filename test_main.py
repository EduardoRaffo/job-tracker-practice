import sqlite3

import pytest
from fastapi.testclient import TestClient

from db import get_db, init_db
from main import app


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_application(auth_client):
    response = auth_client.post(
        "/applications", json={"company": "Acme", "position": "Junior Python"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["company"] == "Acme"
    assert data["status"] == "saved"


def test_get_application_not_found(auth_client):
    response = auth_client.get("/applications/999")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Candidatura no encontrada"


def test_get_application(auth_client):
    response_post = auth_client.post(
        "/applications",
        json={"company": "Acme", "position": "Junior Python", "status": "saved"},
    )
    assert response_post.status_code == 201
    data_post = response_post.json()
    assert data_post["company"] == "Acme"
    assert data_post["status"] == "saved"
    app_id = data_post["id"]
    response_get = auth_client.get(f"/applications/{app_id}")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get == data_post


def test_list_applications(auth_client):
    response_post_1 = auth_client.post(
        "/applications",
        json={"company": "Acme", "position": "Junior Python", "status": "saved"},
    )
    assert response_post_1.status_code == 201
    response_post_2 = auth_client.post(
        "/applications",
        json={"company": "Marvel", "position": "Senior Python", "status": "saved"},
    )
    assert response_post_2.status_code == 201
    list_applications = auth_client.get("/applications")
    assert list_applications.status_code == 200
    assert len(list_applications.json()) == 2
    companies = [a["company"] for a in list_applications.json()]
    assert companies == ["Acme", "Marvel"]


def test_list_applications_empty(auth_client):
    list_applications = auth_client.get("/applications")
    assert list_applications.status_code == 200
    assert list_applications.json() == []


def test_delete_application(auth_client):
    response = auth_client.post(
        "/applications", json={"company": "Acme", "position": "Junior Python"}
    )
    assert response.status_code == 201
    data = response.json()
    app_id = data["id"]
    response_delete = auth_client.delete(f"/applications/{app_id}")
    assert response_delete.status_code == 204
    response_get = auth_client.get(f"/applications/{app_id}")
    assert response_get.status_code == 404


def test_update_application(auth_client):
    response = auth_client.post(
        "/applications", json={"company": "Acme", "position": "Junior Python"}
    )
    assert response.status_code == 201
    data = response.json()
    app_id = data["id"]
    response_patch = auth_client.patch(
        f"/applications/{app_id}", json={"status": "offer"}
    )
    assert response_patch.status_code == 200


def test_update_application_empty_body(auth_client):
    response_post = auth_client.post(
        "/applications", json={"company": "Acme", "position": "Junior Python"}
    )
    assert response_post.status_code == 201
    data_post = response_post.json()
    app_id = data_post["id"]
    response_patch = auth_client.patch(f"/applications/{app_id}", json={})
    assert response_patch.status_code == 200
    data_patch = response_patch.json()
    assert data_patch == data_post


def test_register_user(client):
    email_test = "test@testmail.com"
    password_test = "TestPassword"
    response_post = client.post(
        "/auth/register", json={"email": email_test, "password": password_test}
    )
    assert response_post.status_code == 201
    data_post = response_post.json()
    assert data_post["email"] == email_test
    assert "password" not in data_post
    assert "password_hash" not in data_post
    assert password_test not in response_post.text


def test_register_duplicate_email(client):
    email_test = "test@testmail.com"
    password_test = "TestPassword"
    response_post = client.post(
        "/auth/register", json={"email": email_test, "password": password_test}
    )
    assert response_post.status_code == 201
    response_duplicate = client.post(
        "/auth/register", json={"email": email_test, "password": password_test}
    )
    assert response_duplicate.status_code == 409
    assert response_duplicate.json()["detail"] == "El email ya está registrado"
    response_upper = client.post(
        "/auth/register", json={"email": email_test.upper(), "password": password_test}
    )
    assert response_upper.status_code == 409
    assert response_upper.json()["detail"] == "El email ya está registrado"


def test_register_short_password(client):
    email_test = "test@testmail.com"
    password_short_test = "TPd"
    response_post = client.post(
        "/auth/register", json={"email": email_test, "password": password_short_test}
    )
    assert response_post.status_code == 422
    errors = response_post.json()["detail"]
    assert errors[0]["loc"][-1] == "password"


def test_login_success(client):
    email_test = "test@testmail.com"
    password_test = "StrongPasswrd"
    response_post = client.post(
        "/auth/register", json={"email": email_test, "password": password_test}
    )
    assert response_post.status_code == 201
    response_login_post = client.post(
        "/auth/login", data={"username": email_test, "password": password_test}
    )
    assert response_login_post.status_code == 200
    data_post = response_login_post.json()
    assert data_post["token_type"] == "bearer"
    assert "access_token" in data_post


def test_login_wrong_password(client):
    email_test = "test@testmail.com"
    password_test = "StrongPassword"
    wrong_password = "FakePassword"
    response_post = client.post(
        "/auth/register", json={"email": email_test, "password": password_test}
    )
    assert response_post.status_code == 201
    response_login_post = client.post(
        "/auth/login", data={"username": email_test, "password": wrong_password}
    )
    assert response_login_post.status_code == 401
    data_post = response_login_post.json()
    assert data_post["detail"] == "Credenciales incorrectas"


def test_login_unknown_email(client):
    email_test = "test@testmail.com"
    password_test = "StrongPassword"
    response_login_post = client.post(
        "/auth/login", data={"username": email_test, "password": password_test}
    )
    assert response_login_post.status_code == 401
    data_post = response_login_post.json()
    assert data_post["detail"] == "Credenciales incorrectas"


def test_applications_require_token(client):
    response = client.get("/applications")
    assert response.status_code == 401


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test.db"

    def override_get_db():
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        init_db(conn)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client):
    credentials = {"email": "owner@test.com", "password": "OwnerPass123"}
    client.post("/auth/register", json=credentials)
    response = client.post(
        "/auth/login",
        data={"username": credentials["email"], "password": credentials["password"]},
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
