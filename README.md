# Fast Celery 🛠️

This project is a FastAPI application that uses Celery for background task processing to manage bookings. It uses Redis as a message broker and a SQLite database for persistence.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Docker
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (as the Python package manager)

### How to Run

1.  **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd fast-celery
    ```

2.  **Install Dependencies**
    Use `uv` to create a virtual environment and install the required packages from `pyproject.toml`.
    ```bash
    uv venv
    uv pip install -e .
    ```
    Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```

3.  **Start Background Services**
    This will start the Redis container required for Celery.
    ```bash
    docker-compose up -d
    ```

4.  **Start the Celery Worker**
    In a new terminal, start the Celery worker to process background tasks.
    ```bash
    celery -A app.worker worker --loglevel=info
    ```

5.  **Start the FastAPI Application**
    In another terminal, run the FastAPI server. The database and tables will be created automatically on startup.
    ```bash
    fastapi dev app/main.py
    ```
    The API will be available at `http://localhost:8000`.

## API Endpoints

Here are the available API endpoints:

---

### 1. Create Booking

- **Method:** `POST`
- **Path:** `/bookings`
- **Description:** Creates a new booking, stores it in the database with a `pending` status, and triggers the background processing saga.
- **Request Body:**
  ```json
  {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "1234567890"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "message": "Booking process started",
    "booking_id": 1
  }
  ```
- **Example `curl`:**
  ```bash
  curl -X POST "http://localhost:8000/bookings" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "1234567890"
      }'
  ```

---


### 2. Get Booking Details

- **Method:** `GET`
- **Path:** `/bookings/{booking_id}`
- **Description:** Retrieves the details and current status of a specific booking. The status will change from `pending` to `confirmed` or `cancelled` as the saga progresses.
- **Path Parameters:**
  - `booking_id` (integer): The unique ID of the booking.
- **Success Response (`200 OK`):**
  ```json
  {
    "id": 1,
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "1234567890",
    "status": "confirmed"
  }
  ```
- **Error Response (`404 Not Found`):**
  ```json
  {
    "error": "Booking not found"
  }
  ```
- **Example `curl`:**
  ```bash
  curl http://localhost:8000/bookings/1
  ```

---


### 3. Process Unprocessed Bookings

- **Method:** `GET`
- **Path:** `/bookings/unprocessed`
- **Description:** Triggers a background task to find and re-process any bookings that were not successfully processed (e.g., due to a worker restart).
- **Success Response (`200 OK`):**
  ```json
  {
    "message": "Started processing unprocessed bookings in the background."
  }
  ```
- **Example `curl`:**
  ```bash
  curl http://localhost:8000/bookings/unprocessed
  ```

---


### 4. Root / Health Check

- **Method:** `GET`
- **Path:** `/`
- **Description:** A simple root endpoint to verify that the API is running.
- **Success Response (`200 OK`):**
  ```json
  {
    "message": "Hello World"
  }
  ```