import time
import anyio
import logging
from celery import Celery, chain, Task
from sqlalchemy import select
from .db import db
from .models import Booking

# Configure logging
logger = logging.getLogger(__name__)

app = Celery('tasks',
             broker='redis://localhost:6379/0',
             backend='db+sqlite:///little-fast-celery.db',
             include=["app.worker"])


class PaymentFailed(Exception):
    """Custom exception for payment failures."""
    pass


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, KeyError)
    retry_kwargs = {'max_retries': 5}
    retry_backoff = True


async def _process_payment(booking_id):
    async with db.Session() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            logger.error(f"Booking with id {booking_id} not found for payment processing.")
            return

        logger.info(f"Processing payment for booking_id: {booking_id}")
        time.sleep(2)

        # Simulate a payment failure for even booking ids
        if booking_id % 2 == 0:
            booking.status = "payment_failed"
            await session.commit()
            logger.warning(f"Payment failed for booking_id: {booking_id}. Triggering compensation.")
            raise PaymentFailed(f"Card declined for booking {booking_id}")

        booking.status = "payment_processed"
        await session.commit()
        logger.info(f"Payment processed successfully for booking_id: {booking_id}")


@app.task(bind=True, base=BaseTaskWithRetry)
def process_payment(self, booking_id):
    logger.info(f"{type(self)} -- Starting payment processing for booking_id: {booking_id}")
    anyio.run(_process_payment, booking_id)
    return booking_id


async def _send_confirmation_email(booking_id):
    async with db.Session() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            logger.error(f"Booking with id {booking_id} not found for sending confirmation.")
            return
        logger.info(f"Sending confirmation email for booking_id: {booking_id}")
        time.sleep(2)
        booking.status = "confirmed"
        await session.commit()
        logger.info(f"Booking {booking_id} confirmed and email sent.")


@app.task(bind=True)
def send_confirmation_email(self, booking_id):
    logger.info(f"{type(self)} -- Sending confirmation email for booking_id: {booking_id}")
    anyio.run(_send_confirmation_email, booking_id)
    return booking_id


async def _cancel_booking(booking_id):
    async with db.Session() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            logger.error(f"Booking with id {booking_id} not found for cancellation.")
            return
        booking.status = "cancelled"
        await session.commit()
        logger.warning(f"Booking {booking_id} has been cancelled due to a failure in the saga.")


@app.task(bind=True)
def cancel_booking(self, failed_task_id, booking_id, *args, **kwargs):
    logger.info(f"{type(self)} -- Cancelling booking_id: {booking_id} due to failed task: {failed_task_id}")
    anyio.run(_cancel_booking, booking_id)


@app.task
def booking_saga(booking_id):
    # Create a chain of tasks for the saga
    saga = chain(
        process_payment.s(booking_id),
        send_confirmation_email.s(),
    ).on_error(cancel_booking.s(booking_id))

    # Execute the saga
    saga.apply_async()


async def _get_unprocessed_bookings():
    async with db.Session() as session:
        unprocessed = await session.execute(
            select(Booking).where(Booking.status == "pending")
        )
        return unprocessed.scalars().all()


@app.task
def get_unprocessed_bookings():
    """
    Checks for bookings that have not been processed yet.
    """
    logger.info("Checking for unprocessed bookings.")
    unprocessed_bookings = anyio.run(_get_unprocessed_bookings)
    booking_ids = [b.id for b in unprocessed_bookings]
    logger.info(f"Found {len(booking_ids)} unprocessed bookings: {booking_ids}")
    return booking_ids
