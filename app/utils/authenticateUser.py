from passlib.context import CryptContext
from app.models import User
from sqlalchemy import or_
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def authenticate_user(user_pass, password: str, db):
    user = (
        db.query(User)
        .filter(or_(User.email == user_pass, User.user_matric == user_pass))
        .first()
    )

    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user
