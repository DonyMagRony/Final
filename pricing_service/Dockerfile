FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app


COPY ./pricing_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./pricing_service /app/pricing_service

EXPOSE 8002


CMD ["uvicorn", "pricing_service.main:app", "--host", "0.0.0.0", "--port", "8002"]