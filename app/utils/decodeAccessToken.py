from jose import jwt, JWTError
import os
from dotenv import load_dotenv
from fastapi import HTTPException, status

if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        username = payload.get("username")
        role = payload.get("role")
        user_matric = payload.get("user_matric")

        if not all([email, username, role, user_matric]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user",
            )

        return {
            "email": email,
            "username": username,
            "role": role,
            "user_matric": user_matric,
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user.",
        )
