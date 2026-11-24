import sqlite3
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field

from db import get_db
from security import create_access_token, decode_access_token

app = FastAPI()
hasher = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
    status: Status | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    id: int
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Application(ApplicationCreate):
    id: int


def get_or_404(db, app_id, user_id):
    check = db.execute(
        "SELECT * FROM applications WHERE id = ? AND user_id = ?",
        (
            app_id,
            user_id,
        ),
    ).fetchone()
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidatura no encontrada",
        )
    return Application(**dict(check))


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: sqlite3.Connection = Depends(get_db),
) -> UserPublic:
    user_id = decode_access_token(token)
    user = None
    if user_id is not None:
        user = db.execute(
            "SELECT id, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o caducado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserPublic(id=user["id"], email=user["email"])


@app.post(
    "/applications", response_model=Application, status_code=status.HTTP_201_CREATED
)
def create_application(
    payload: ApplicationCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    cur = db.execute(
        "INSERT INTO applications (company, position, status, user_id) VALUES (?, ?, ?, ?)",
        (
            payload.company,
            payload.position,
            payload.status.value,
            current_user.id,
        ),
    )
    db.commit()
    return Application(id=cur.lastrowid, **payload.model_dump())


@app.post(
    "/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate, db: sqlite3.Connection = Depends(get_db)):
    email = payload.email.lower()
    hashed = hasher.hash(payload.password)
    try:
        cur = db.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (
                email,
                hashed,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado",
        )
    return UserPublic(id=cur.lastrowid, email=email)


@app.post("/auth/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db),
):
    # Buscar al usuario por email
    user = db.execute(
        "SELECT id, password_hash FROM users WHERE email = ?",
        (form.username.lower(),),
    ).fetchone()

    # Comprobar usuario y contraseña
    if user is None or not hasher.verify(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user["id"]))


@app.get("/auth/me", response_model=UserPublic)
def read_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user


@app.get("/applications", response_model=list[Application])
def list_applications(
    db: sqlite3.Connection = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    rows = db.execute(
        "SELECT * FROM applications WHERE user_id = ? ORDER BY id", (current_user.id,)
    )
    return [Application(**dict(r)) for r in rows]


@app.get("/applications/{app_id}", response_model=Application)
def get_application(
    app_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    return get_or_404(db, app_id, current_user.id)


@app.patch("/applications/{app_id}", response_model=Application)
def update_application(
    app_id: int,
    payload: ApplicationUpdate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    get_or_404(db, app_id, current_user.id)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True, mode="json")
    if changes:
        columns = ",".join(f"{col} = ?" for col in changes)
        db.execute(
            f"UPDATE applications SET {columns} WHERE id = ?",
            (*changes.values(), app_id),
        )
        db.commit()

    return get_or_404(db, app_id, current_user.id)


@app.delete("/applications/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def del_application(
    app_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    get_or_404(db, app_id, current_user.id)
    db.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    db.commit()
