# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., for psycopg2 later)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./order_manager /app/order_manager

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# Use uvicorn to run the FastAPI application
# --host 0.0.0.0 makes it accessible from outside the container
# --reload is useful for development, remove for production
CMD ["uvicorn", "order_manager.main:app", "--host", "0.0.0.0", "--port", "8000"]