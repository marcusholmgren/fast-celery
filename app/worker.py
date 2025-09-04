"""
This module contains the Celery worker and tasks for the booking service.
"""
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
    """
    Base task with automatic retry mechanism.
    """
    autoretry_for = (Exception, KeyError)
    retry_kwargs = {'max_retries': 5}
    retry_backoff = True


async def _process_payment(booking_id):
    """
    Helper function to process the payment for a booking.

    Args:
        booking_id (int): The ID of the booking to process the payment for.
    """
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
    """
    Celery task to process the payment for a booking.

    Args:
        booking_id (int): The ID of the booking to process the payment for.
    """
    logger.info(f"{type(self)} -- Starting payment processing for booking_id: {booking_id}")
    anyio.run(_process_payment, booking_id)
    return booking_id


async def _send_confirmation_email(booking_id):
    """
    Helper function to send a confirmation email for a booking.

    Args:
        booking_id (int): The ID of the booking to send the confirmation email for.
    """
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
    """
    Celery task to send a confirmation email for a booking.

    Args:
        booking_id (int): The ID of the booking to send the confirmation email for.
    """
    logger.info(f"{type(self)} -- Sending confirmation email for booking_id: {booking_id}")
    anyio.run(_send_confirmation_email, booking_id)
    return booking_id


async def _cancel_booking(booking_id):
    """
    Helper function to cancel a booking.

    Args:
        booking_id (int): The ID of the booking to cancel.
    """
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
    """
    Celery task to cancel a booking. This is used as an error handler in the booking saga.

    Args:
        failed_task_id (str): The ID of the task that failed.
        booking_id (int): The ID of the booking to cancel.
    """
    logger.info(f"{type(self)} -- Cancelling booking_id: {booking_id} due to failed task: {failed_task_id}")
    anyio.run(_cancel_booking, booking_id)


@app.task
def booking_saga(booking_id):
    """
    Celery task that orchestrates the booking saga.
    The saga is a chain of tasks that are executed in order.
    If any task in the chain fails, the `cancel_booking` task is called.

    Args:
        booking_id (int): The ID of the booking to start the saga for.
    """
    # Create a chain of tasks for the saga.
    # The chain consists of processing the payment and sending a confirmation email.
    # If any of these tasks fail, the `on_error` handler is called, which cancels the booking.
    saga = chain(
        process_payment.s(booking_id),
        send_confirmation_email.s(),
    ).on_error(cancel_booking.s(booking_id))

    # Execute the saga asynchronously.
    saga.apply_async()


async def _get_unprocessed_bookings():
    """
    Helper function to get all unprocessed bookings from the database.
    """
    async with db.Session() as session:
        unprocessed = await session.execute(
            select(Booking).where(Booking.status == "pending")
        )
        return unprocessed.scalars().all()


@app.task
def get_unprocessed_bookings():
    """
    Celery task to get all unprocessed bookings and return their IDs.
    """
    logger.info("Checking for unprocessed bookings.")
    unprocessed_bookings = anyio.run(_get_unprocessed_bookings)
    booking_ids = [b.id for b in unprocessed_bookings]
    logger.info(f"Found {len(booking_ids)} unprocessed bookings: {booking_ids}")
    return booking_ids
