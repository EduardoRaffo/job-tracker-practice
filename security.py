import os

from datetime import datetime, timedelta, timezone
import jwt
from dotenv import load_dotenv

load_dotenv()


SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(user_id: int) -> str:
    expire = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": (datetime.now(timezone.utc) + expire)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token
