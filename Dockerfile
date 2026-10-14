FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . /app/
RUN mkdir -p /app/media /app/staticfiles && chown -R app:app /app/media /app/staticfiles
USER app
RUN DJANGO_DEBUG=True DJANGO_DB_ENGINE=sqlite DJANGO_SECRET_KEY=build-only-not-a-production-secret SMS_ASYNC=False python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "onlineshop.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--error-logfile", "-"]
