from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship

from database.database import Base


class User(Base):
    __tablename__ = "Users"

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_matric = Column(String(50), unique=True)
    email = Column(String(60), unique=True)
    username = Column(String(60))
    hashed_password = Column(String(128))
    role = Column(String(15))

    geofences = relationship("Geofence", back_populates="creator")

class Geofence(Base):
    __tablename__ = "Geofences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fence_code = Column(String(15), unique=True)
    name = Column(String(60))
    latitude = Column(Float)
    longitude = Column(Float)
    radius = Column(Float)
    fence_type = Column(String(60))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String(60))

    #foreign key
    creator_matric = Column(String(50), ForeignKey("Users.user_matric"))

    creator = relationship("User", back_populates="geofences")

class AttendanceRecord(Base):
    __tablename__ = "AttendanceRecords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_matric = Column(String(50), ForeignKey("Users.user_matric"))
    fence_code = Column(String(15), ForeignKey("Geofences.fence_code"))
    geofence_name = Column(String(60))
    timestamp = Column(DateTime)
    matric_fence_code = Column(String(60))