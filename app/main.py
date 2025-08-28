from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from .models import Booking, BookingCommand
from .worker import booking_saga, get_unprocessed_bookings
from .db import create_db_and_tables, get_db_session


@asynccontextmanager
async def lifespan(api_app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/bookings")
async def create_booking(booking_cmd: BookingCommand, db: AsyncSession = Depends(get_db_session)):
    booking = Booking(**booking_cmd.model_dump(), status="pending")
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    booking_saga.delay(booking.id)
    return {"message": "Booking process started", "booking_id": booking.id}


@app.get("/bookings/unprocessed")
async def fetch_unprocessed_bookings(background_tasks: BackgroundTasks):
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
    booking = await db.get(Booking, booking_id)
    if not booking:
        return {"error": "Booking not found"}, 404
    return booking
