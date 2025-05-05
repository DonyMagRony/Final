# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed for psycopg2-binary or other libraries
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./inventory_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
# Copy the specific service directory content
COPY ./inventory_service /app/inventory_service

# Expose the port the app runs on (must match config.APP_PORT)
EXPOSE 8001

# Define the command to run the application using Uvicorn
CMD ["uvicorn", "inventory_service.main:app", "--host", "0.0.0.0", "--port", "8001"]