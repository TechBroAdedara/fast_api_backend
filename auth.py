import secrets
from datetime import datetime, timedelta
from typing import Annotated, Tuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette import status
import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from mysql.connector.errors import IntegrityError

router = APIRouter(prefix="/auth", tags=["auth"])

secret_key = secrets.token_hex(16)
SECRET_KEY = secret_key
ALGORITHM = "HS256"

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

class CreateUserRequest(BaseModel):
    user_matric: str
    username: str
    password: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_db():
    db = mysql.connector.connect(
        host="sql8.freesqldatabase.com",
        user="sql8714187",
        passwd="CIng3QVDUe",
        database="sql8714187"
    )
    try:
        cursor = db.cursor(dictionary=True)  # Use dictionary cursor for better readability
        yield db, cursor
    finally:
        cursor.close()
        db.close()

db_dependency = Annotated[Tuple[MySQLConnection, MySQLCursorDict], Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db_tuple: db_dependency, create_user_request: CreateUserRequest):
    db, cursor = db_tuple
    hashed_password = bcrypt_context.hash(create_user_request.password)
    query = """
    INSERT INTO Users (user_matric, username, hashed_password, role) VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (create_user_request.user_matric, create_user_request.username, hashed_password, create_user_request.role))
        db.commit()
    except IntegrityError as e:
        if e.errno == 1062:  # Duplicate entry error code
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{create_user_request.username}' already exists."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while creating the user."
            )
    return {"message": "User created successfully"}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db_tuple: db_dependency):
    db, cursor = db_tuple
    user = authenticate_user(form_data.username, form_data.password, cursor)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user."
        )
    token = create_access_token(user['username'], user['user_matric'], timedelta(minutes=20))
    return {"access_token": token, "token_type": "bearer"}

def authenticate_user(username: str, password: str, cursor: MySQLCursorDict):
    query = "SELECT * FROM Users WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()
    if not user:
        return False
    if not bcrypt_context.verify(password, user['hashed_password']):
        return False
    return user

def create_access_token(username: str, user_matric: str, expires_delta: timedelta):
    encode = {"sub": username, "id": user_matric}
    expires = datetime.utcnow() + expires_delta
    encode.update({"exp": expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate user.'
            )
        return {"username": username, 'id': user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate user.'
        )

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_matric: str = payload.get('id')
        if username is None or user_matric is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Could not validate user")
        return {"username": username, "id": user_matric}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Could not validate user.")