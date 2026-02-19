#!/bin/sh
# Pipeline cron entrypoint
# Exports env vars so cron jobs inherit them, then starts crond in foreground.

# Write all current env vars to a file that cron jobs can source
env > /app/.env.docker

# Write crontab: run pipeline daily at 7 AM (container TZ=America/Denver)
echo "0 7 * * * . /app/.env.docker; cd /app && /usr/local/bin/python scripts/pipeline.py --verbose >> /proc/1/fd/1 2>&1" | crontab -

# Start cron in foreground
exec crond -f -l 2
