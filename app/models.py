from typing import Literal, ClassVar
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String
from alchemical import Model

BookingStatus = Literal["pending", "payment_failed", "payment_processed", "confirmed", "cancelled"]


class Booking(Model):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    status: ClassVar[BookingStatus] = Column(String, default="pending")


class BookingCommand(BaseModel):
    name: str = Field(..., min_length=2, description="Name of the person making the booking")
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
                       description="Email address of the person making the booking")
    phone: str = Field(..., description="Phone number of the person making the booking")
