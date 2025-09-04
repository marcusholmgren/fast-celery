"""
This module contains the main FastAPI application for the booking service.
"""
from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from .models import Booking, BookingCommand
from .worker import booking_saga, get_unprocessed_bookings
from .db import create_db_and_tables, get_db_session


@asynccontextmanager
async def lifespan(api_app: FastAPI):
    """
    Asynchronous context manager for the lifespan of the FastAPI application.
    It creates the database and tables on startup.

    Args:
        api_app (FastAPI): The FastAPI application instance.
    """
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """
    Root endpoint for the API.
    """
    return {"message": "Hello World"}


@app.post("/bookings")
async def create_booking(booking_cmd: BookingCommand, db: AsyncSession = Depends(get_db_session)):
    """
    Creates a new booking and starts the booking saga.

    Args:
        booking_cmd (BookingCommand): The booking command with the booking details.
        db (AsyncSession): The database session.

    Returns:
        dict: A message indicating that the booking process has started and the booking ID.
    """
    booking = Booking(**booking_cmd.model_dump(), status="pending")
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    booking_saga.delay(booking.id)
    return {"message": "Booking process started", "booking_id": booking.id}


@app.get("/bookings/unprocessed")
async def fetch_unprocessed_bookings(background_tasks: BackgroundTasks):
    """
    Fetches unprocessed bookings and triggers the booking saga for each in the background.

    Args:
        background_tasks (BackgroundTasks): The background tasks manager.

    Returns:
        dict: A message indicating that the processing of unprocessed bookings has started.
    """
    def process_unprocessed():
        """
        Fetches unprocessed bookings and triggers the booking saga for each.
        """
        task = get_unprocessed_bookings.delay()
        unprocessed_ids = task.get()
        for booking_id in unprocessed_ids:
            booking_saga.delay(booking_id)

    background_tasks.add_task(process_unprocessed)
    return {"message": "Started processing unprocessed bookings in the background."}


@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db_session)):
    """
    Retrieves a booking by its ID.

    Args:
        booking_id (int): The ID of the booking to retrieve.
        db (AsyncSession): The database session.

    Returns:
        Booking or dict: The booking object if found, otherwise an error message.
    """
    booking = await db.get(Booking, booking_id)
    if not booking:
        return {"error": "Booking not found"}, 404
    return booking
