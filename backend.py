import json
import math
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import auth
from auth import get_current_user
from database import SessionLocal, init_db
from models import AttendanceRecord, Geofence, User
from schemas import GeofenceCreate, UserCreate


# ----------------------------------------Geolocation Logic/Algorithm--------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return (
        2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 1000
    )  # Convert to meters


def check_user_in_circular_geofence(user_lat, user_lng, geofence):
    latitude = geofence.latitude
    longitude = geofence.longitude
    radius = geofence.radius
    distance = haversine(user_lat, user_lng, latitude, longitude)
    return distance <= radius


# ----------------------------------------Password Hashing--------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----------------------------------------FastAPI App Init--------------------------------------------
app = FastAPI()
app.include_router(auth.router)


# ----------------------------------------Dependency--------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------------------Routes--------------------------------------------


# Endpoint to get the list of users
@app.get("/getUsers")
def getUsers(db: SessionLocal = Depends(get_db)):
    db_users = db.query(User).all()
    return db_users


# Endpoint to create Geofence
@app.post("/geofences/", response_model=dict)
def create_geofence(geofence: GeofenceCreate, db: SessionLocal = Depends(get_db)):
    db_geofence = db.query(Geofence).filter(Geofence.name == Geofence.name).first()
    if db_geofence:
        raise HTTPException(status_code=400, detail="Geofence already active")

    new_geofence = Geofence(**geofence.dict())
    db.add(new_geofence)
    db.commit()
    db.refresh(new_geofence)
    return {"id": new_geofence.id, "name": new_geofence.name}


# Endpoint to get a list of Geofences
@app.get("/listGeofences")
def listGeofences(db: SessionLocal = Depends(get_db)):
    geofences = db.query(Geofence).all()
    return "List of available geofences: ", geofences


# Endpoint to validate user attendance and store in database
@app.get("/validateGeofence/")
def validateGeofence(user_id: int, geofence_id: int, lat, long, db: SessionLocal = Depends(get_db)):  # type: ignore
    db_user = db.query(User).filter(User.id == user_id).first()
    db_attendance = (
        db.query(AttendanceRecord).filter(AttendanceRecord.user_id == user_id).first()
    )

    # error handlers
    if db_user is None:
        return "User isn't on database"
    if db_attendance:
        return f"Attendance for user {db_user.id} is already recorded."

    geofence = db.query(Geofence).first()
    user_latitude = float(lat)
    user_longitude = float(long)

    if geofence.fenceType == "circle":
        if check_user_in_circular_geofence(user_latitude, user_longitude, geofence):
            attendance_record = AttendanceRecord(
                user_id=user_id, geofence_id=geofence_id
            )
            db.add(attendance_record)
            db.commit()
            db.refresh(attendance_record)
            return {
                "id": attendance_record.id,
                "timestamp": attendance_record.timestamp,
            }
        # return(f"User is within geofence: {geofence['name']}")
        else:
            return "User is not within the geofence"
    return geofence


@app.get("/listAttendance")
def ListAttendance(db: SessionLocal = Depends(get_db)):
    db_attendance = db.query(AttendanceRecord).all()
    return db_attendance


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
