from pydantic import EmailStr
from datetime import timedelta, datetime
from jose import JWTError, jwt

import os
from dotenv import load_dotenv
if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM") 

def create_access_token(
    email: EmailStr,
    username: str,
    role: str,
    user_matric: str,
    expires_delta: timedelta,
):
    data_to_encode = {
        "sub": email,
        "username": username,
        "role": role,
        "user_matric": user_matric,
    }
    expires = datetime.utcnow() + expires_delta
    data_to_encode.update({"exp": expires})
    return jwt.encode(data_to_encode, SECRET_KEY, algorithm=ALGORITHM)
