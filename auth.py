import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Annotated, Tuple, Optional, Dict

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from mysql.connector.errors import IntegrityError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from starlette import status

if os.getenv('ENVIRONMENT') == 'development':
    load_dotenv()
    

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = str(os.getenv('SECRET_KEY'))
ALGORITHM = "HS256"

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token/")


class CreateUserRequest(BaseModel):
    email: EmailStr
    user_matric: str
    username: str
    password: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    role: str | None = None


def get_db():
    db = mysql.connector.connect(
        host= os.getenv("DB_HOST"), 
        user=os.getenv("DB_USER"), 
        passwd=os.getenv("DB_PSWORD"), 
        database=os.getenv("DB_DB")
    )
    try:
        cursor = db.cursor(dictionary=True) 
        yield db, cursor
    finally:
        cursor.close()
        db.close()


db_dependency = Annotated[Tuple[MySQLConnection, MySQLCursorDict], Depends(get_db)]


@router.post("/create_user/", status_code=status.HTTP_201_CREATED)
async def create_user(db_tuple: db_dependency, create_user_request: CreateUserRequest):
    db, cursor = db_tuple
    hashed_password = bcrypt_context.hash(create_user_request.password)
    query = """
    INSERT INTO Users (email, user_matric, username, hashed_password, role) VALUES (%s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(
            query,
            (
                create_user_request.email,
                create_user_request.user_matric,
                create_user_request.username,
                hashed_password,
                create_user_request.role.lower(),
            ),
        )
        db.commit()
    except IntegrityError as e:
        if e.errno == 1062:  # Duplicate entry error code
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail= "ID number/Email account already exists. Login?",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while creating the user.",
            )
    return {"message": "User created successfully"}


@router.post("/token/", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db_tuple: db_dependency
):
    db, cursor = db_tuple

    userQuery = "SELECT * FROM Users WHERE email = %s"

    cursor.execute(userQuery, (form_data.username,))
    userCheck = cursor.fetchone()

    if not userCheck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail = "User not registered yet"
        )
    
    user = authenticate_user(form_data.username, form_data.password, cursor)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password incorrect")
        
    token = create_access_token(
        user['email'], user['username'], user["role"], user["user_matric"], timedelta(minutes=20)
        )
    return {"access_token": token, "token_type": "bearer"}


def authenticate_user(email: EmailStr, password: str, cursor: MySQLCursorDict):
    query = "SELECT * FROM Users WHERE email = %s"
    cursor.execute(query, (email,))
    user = cursor.fetchone()
    if not bcrypt_context.verify(password, user["hashed_password"]):
        return False
    return user


def create_access_token(email: EmailStr, username: str, role: str, user_matric: str, expires_delta: timedelta):
    encode = {"sub": email, "username": username, "role": role, "user_matric": user_matric }
    expires = datetime.utcnow() + expires_delta
    encode.update({"exp": expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get('sub')
        username= payload.get("username")
        role= payload.get("role")
        user_matric= payload.get("user_matric")

        if not all([email, username, role, user_matric]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user",
            )
        
        return {"email": email, "username": username, "role": role, "user_matric": user_matric}
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
