#!/usr/bin/env sh

./manage.py collectstatic --noinput
uwsgi --http "0.0.0.0:${PORT}" --module walletwatch.wsgi --master --processes 4 --threads 2