# Models
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # 'admin' or 'student'

class Geofence(Base):
    __tablename__ = "Geofences"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    radius = Column(Float)
    fenceType= Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    
class AttendanceRecord(Base):
    __tablename__ = "Attendance_Records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("Users.id"))
    geofence_id = Column(Integer, ForeignKey("Geofences.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)