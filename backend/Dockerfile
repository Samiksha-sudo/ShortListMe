FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Migrations run at start-up (this replaced the Alembic upgrade that used to run in the app lifespan).
CMD ["sh", "-c", "python manage.py migrate --noinput --fake-initial && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 8 --timeout 240"]
