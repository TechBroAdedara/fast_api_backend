import json
import math
from typing import List, Generator, Annotated,Tuple

import mysql.connector
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from passlib.context import CryptContext

import auth
from auth import get_current_user
from schemas import GeofenceCreate


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
    latitude = geofence['latitude']
    longitude = geofence['longitude']
    radius = geofence['radius']
    distance = haversine(user_lat, user_lng, latitude, longitude)
    return distance <= radius


# ----------------------------------------Password Hashing--------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----------------------------------------FastAPI App Init--------------------------------------------
app = FastAPI()
app.include_router(auth.router)


# ----------------------------------------Dependency--------------------------------------------
def get_db() -> Generator:
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
user_dependency = Annotated[dict, Depends(get_current_user)]
# ----------------------------------------Routes--------------------------------------------

@app.get("/", status_code=status.HTTP_200_OK)
async def user(user:user_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed")
    
    return {"User": user}

# Endpoint to get the list of users
@app.get("/get_users")
def get_users(db_tuple:db_dependency):
    db, cursor = db_tuple
    cursor.execute("SELECT * FROM Users")
    result = cursor.fetchall()
    return result

# Endpoint to create Geofence
@app.post("/geofences/")
def create_geofence(geofence: GeofenceCreate, db_tuple: db_dependency):
    db, cursor = db_tuple
    cursor.execute("SELECT * FROM Geofences WHERE name = %s", (geofence.name,))
    db_geofence = cursor.fetchone()
    if db_geofence:
        raise HTTPException(status_code=400, detail="Geofence already exists")

    cursor.execute(
        "INSERT INTO Geofences (name, latitude, longitude, radius, fence_type) VALUES (%s, %s, %s, %s, %s)",
        (geofence.name, geofence.latitude, geofence.longitude, geofence.radius, geofence.fence_type)
    )
    db.commit()
    return {"id": cursor.lastrowid, "name": geofence.name}

# Endpoint to get a list of Geofences
@app.get("/get_geofences")
def list_geofences(db_tuple:db_dependency):
    db, cursor = db_tuple
    cursor.execute("SELECT * FROM Geofences")
    geofences = cursor.fetchall()
    return {"geofences": geofences}

# Endpoint to validate user attendance and store in database
@app.get("/validateGeofence/")
def validate_geofence(user_matric: str, geofence_name: str, lat: float, long: float, db_tuple: db_dependency):
    db, cursor = db_tuple
    cursor.execute("SELECT * FROM Users WHERE user_matric = %s", (user_matric,))
    db_user = cursor.fetchone()

    cursor.execute("SELECT * FROM AttendanceRecords WHERE user_matric = %s", (user_matric,))
    db_attendance = cursor.fetchone()

    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if db_attendance:
        return f"Attendance for user {db_user['user_matric']} is already recorded."

    cursor.execute("SELECT * FROM Geofences WHERE name = %s", (geofence_name,))
    geofence = cursor.fetchone()
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence not found")
    if geofence['fence_type'] == "circle":
        if check_user_in_circular_geofence(lat, long, geofence):
            cursor.execute(
                "INSERT INTO AttendanceRecords (user_matric, geofence_name) VALUES (%s, %s)",
                (user_matric, geofence_name)
            )
            db.commit()
            return {"message": "Attendance recorded successfully"}
        else:
            return {"message": "User is not within the geofence"}
    else:
        return {"message": "Geofence type not supported"}

# Endpoint to list all attendance records
@app.get("/listAttendance")
def list_attendance(db_tuple:db_dependency):
    db, cursor = db_tuple
    cursor.execute("SELECT * FROM AttendanceRecords")
    attendances = cursor.fetchall()
    return {"attendances": attendances}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
