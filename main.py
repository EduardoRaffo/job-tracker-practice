import sqlite3
from fastapi import FastAPI, HTTPException, Depends, status
from enum import Enum
from pydantic import BaseModel, EmailStr, Field

app = FastAPI()
DB_PATH = "tracker.db"

def get_db():
    conn =  sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'saved'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    try:
        yield conn
    finally:
        conn.close()
@app.get("/health")
def health():
    return {"status": "ok"}


class Status(str, Enum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"

class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    position: str = Field(min_length=1, max_length=120)
    status: Status = Status.saved

class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=120)
    position: str | None = Field(default=None, min_length=1, max_length=120)
    status: Status = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class UserPublic(BaseModel):
    id: int
    email: EmailStr



class Application(ApplicationCreate):
    id: int

def get_or_404(db, app_id):
    check = db.execute(
        "Select * From applications Where id = ?", (app_id,)).fetchone()
    if check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Candidatura no encontrada",   
    )
    return Application(**dict(check))
@app.post("/applications", response_model=Application, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: sqlite3.Connection = Depends(get_db)
):
    cur = db.execute(
        "INSERT INTO applications (company, position, status) VALUES (?, ?, ?)",
    (payload.company, payload.position, payload.status.value),
    )
    db.commit()
    return Application(id=cur.lastrowid, **payload.model_dump())

@app.get("/applications",response_model=list[Application])
def list_applications(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM applications ORDER BY id")
    return [Application(**dict(r)) for r in rows]

@app.get("/applications/{app_id}", response_model=Application)
def get_application(app_id: int, db: sqlite3.Connection = Depends(get_db)):
    return(get_or_404(db, app_id))

@app.patch("/applications/{app_id}", response_model=Application)
def update_application(app_id: int, payload: ApplicationUpdate, db: sqlite3.Connection = Depends(get_db),
                       ):
    get_or_404(db, app_id)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True, mode="json")
    if changes:
        columns = ",".join(f"{col} = ?" for col in changes)
        db.execute(
            f"UPDATE applications SET {columns} WHERE id = ?",
            (*changes.values(), app_id)
        )
        db.commit()
    
    return get_or_404(db, app_id)
    
@app.delete("/applications/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def del_application(app_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_or_404(db, app_id)
    db.execute("DELETE FROM applications WHERE id = ?",(app_id,))
    db.commit()
    