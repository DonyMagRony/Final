# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./order_manager /app/order_manager

EXPOSE 8000

CMD ["uvicorn", "order_manager.main:app", "--host", "0.0.0.0", "--port", "8000"]