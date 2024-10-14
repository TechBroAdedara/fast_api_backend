from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship

from app.database.session import Base

class AttendanceRecord(Base):
    __tablename__ = "AttendanceRecords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_matric = Column(String(50), ForeignKey("Users.user_matric"))
    fence_code = Column(String(15), ForeignKey("Geofences.fence_code"))
    geofence_name = Column(String(60))
    timestamp = Column(DateTime)
    matric_fence_code = Column(String(60))