FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./inventory_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./inventory_service /app/inventory_service

EXPOSE 8001

CMD ["uvicorn", "inventory_service.main:app", "--host", "0.0.0.0", "--port", "8001"]