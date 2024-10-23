import logging
import os
from datetime import timedelta
from dotenv import load_dotenv
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from passlib.context import CryptContext
from starlette import status
from app.schemas.user import CreateUserRequest
from app.schemas.accessToken import Token, TokenData

from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.user import User
from app.database.session import get_db
from app.utils import authenticate_user, create_access_token, decode_token

if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()


router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

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
