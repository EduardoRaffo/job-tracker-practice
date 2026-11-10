import sqlite3
import pytest
from fastapi.testclient import TestClient
from main import app, get_db 


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_application(client):
    response = client.post("/applications", json={"company": "Acme", "position": "Junior Python"})
    assert response.status_code == 201
    data = response.json()
    assert data["company"] == "Acme"
    assert data["status"] == "saved"


def test_get_application_not_found(client):
    response = client.get("/applications/999")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Candidatura no encontrada"


def test_get_application(client):
    response_post = client.post("/applications", json={"company": "Acme", "position": "Junior Python", "status": "saved"})
    assert response_post.status_code == 201
    data_post = response_post.json()
    assert data_post["company"] == "Acme"
    assert data_post["status"] == "saved"
    app_id = data_post["id"]
    response_get = client.get(f"/applications/{app_id}")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get == data_post


def test_list_applications(client):
    response_post_1 = client.post("/applications", json={"company": "Acme", "position": "Junior Python", "status": "saved"})
    assert response_post_1.status_code == 201
    response_post_2 = client.post("/applications", json={"company": "Marvel", "position": "Senior Python", "status": "saved"})
    assert response_post_2.status_code == 201
    list_applications = client.get("/applications")
    assert list_applications.status_code == 200
    assert len(list_applications.json()) == 2
    companies = [a["company"] for a in list_applications.json()]
    assert companies == ["Acme", "Marvel"]

def test_list_applications_empty(client):
    list_applications = client.get("/applications")
    assert list_applications.status_code == 200
    assert list_applications.json() == []

def test_delete_application(client):
    response = client.post("/applications", json={"company": "Acme", "position": "Junior Python"})
    assert response.status_code == 201
    data = response.json()
    app_id = data["id"]
    response_delete = client.delete(f"/applications/{app_id}")
    assert response_delete.status_code == 204
    response_get = client.get(f"/applications/{app_id}")
    assert response_get.status_code == 404

def test_update_application(client):
    response = client.post("/applications", json={"company": "Acme", "position": "Junior Python"})
    assert response.status_code == 201
    data = response.json()
    app_id = data["id"]    
    response_patch = client.patch(f"/applications/{app_id}", json={"status": "offer"})
    assert response_patch.status_code == 200 

def test_update_application_empty_body(client):
    response_post = client.post("/applications", json={"company": "Acme", "position": "Junior Python"})
    assert response_post.status_code == 201
    data_post = response_post.json()
    app_id = data_post["id"]
    response_patch = client.patch(f"/applications/{app_id}", json={})
    assert response_patch.status_code == 200
    data_patch = response_patch.json()
    assert data_patch == data_post
    
    

@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test.db"

    def override_get_db():
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'saved'
                )
                """)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()