#!/usr/bin/env bash
set -eux
python manage.py migrate
python manage.py collectstatic  --noinput
gunicorn server.wsgi -w 4  -b 0.0.0.0:8000 --access-logfile - --error-logfile - --log-level info
