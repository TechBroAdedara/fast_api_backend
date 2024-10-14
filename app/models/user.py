from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship

from app.database.session import Base

class User(Base):
    __tablename__ = "Users"

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_matric = Column(String(50), unique=True)
    email = Column(String(60), unique=True)
    username = Column(String(60))
    hashed_password = Column(String(128))
    role = Column(String(15))

    geofences = relationship("Geofence", back_populates="creator")
