#!/usr/bin/env sh

# Collect static files
echo "Collect static files"
./manage.py collectstatic --noinput


echo "Waiting for DB"
while ! mysqladmin ping -h"db" --silent; do
    sleep 1
done



# Apply database migrations
echo "Apply database migrations"
./manage.py migrate

echo "Starting crond"
crond -L /dev/stdout

# Start server
echo "Starting server"
uwsgi --http "0.0.0.0:${PORT}" --module walletwatch.wsgi  --master --processes 4 --threads 2
