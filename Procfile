release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
web: gunicorn lostfound.wsgi:application --bind 0.0.0.0:$PORT
