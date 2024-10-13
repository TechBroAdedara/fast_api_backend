import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Annotated, Tuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from mysql.connector.errors import IntegrityError
from passlib.context import CryptContext
from pydantic import EmailStr
from starlette import status
from sqlalchemy.exc import IntegrityError
from auth.schemas import CreateUserRequest, Token, TokenData

from sqlalchemy import or_
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import User, Geofence, AttendanceRecord

if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()


def get_db():
    db = SessionLocal()  # Create a new session
    try:
        yield db  # Yield the session to be used
    finally:
        db.close()  # Close the session when done


router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token/")


db_dependency = Annotated[Session, Depends(get_db)]


# --------------------------------------------------------------------------------------
@router.post("/create_user/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, new_user: CreateUserRequest):

    hashed_password = bcrypt_context.hash(new_user.password)
    existing_user = (
        db.query(User)
        .filter(
            or_(
                User.user_matric == new_user.user_matric,
                User.email == new_user.email,
            )
        )
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID number/Email account already exists. Login?",
        )
    try:

        new_user = User(
            email=new_user.email,
            user_matric=new_user.user_matric,
            username=new_user.username,
            hashed_password=hashed_password,
            role=new_user.role.lower(),
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"message": "User created successfully"}
    except Exception as e:
        db.rollback()
        # Capture any other generic exceptions for better error handling
        logging.error(f"General error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Internal error. Please try again or contact admin.",
        )


@router.post("/token/", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency
):

    existing_user = (
        db.query(User)
        .filter(
            or_(
                User.email == form_data.username, User.user_matric == form_data.username
            )
        )
        .first()
    )

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not registered yet"
        )

    authenticated_user = authenticate_user(form_data.username, form_data.password, db)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password incorrect",
        )

    token = create_access_token(
        authenticated_user.email,
        authenticated_user.username,
        authenticated_user.role,
        authenticated_user.user_matric,
        timedelta(minutes=20),
    )
    return {"access_token": token, "token_type": "bearer"}


def authenticate_user(user_pass, password: str, db):
    user = (
        db.query(User)
        .filter(or_(User.email == user_pass, User.user_matric == user_pass))
        .first()
    )

    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


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


def get_current_user(token: str = Depends(oauth2_bearer)):
    return decode_token(token)


def get_current_admin_user(current_user: TokenData = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


def get_current_student_user(current_user: TokenData = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user
