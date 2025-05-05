# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install Python dependencies
# Copy requirements first to leverage Docker cache
COPY ./pricing_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./pricing_service /app/pricing_service

# Expose the port the app runs on (must match config.APP_PORT)
EXPOSE 8002

# Define the command to run the application using Uvicorn
# Ensure the module path is correct: package_name.module:app_variable
CMD ["uvicorn", "pricing_service.main:app", "--host", "0.0.0.0", "--port", "8002"]