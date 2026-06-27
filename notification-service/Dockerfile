FROM python:3.12-slim

WORKDIR /app

COPY notification-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY notification-service/app/ ./app/

CMD ["python", "-m", "app.consumer"]
