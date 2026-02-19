#!/bin/sh
# Pipeline cron entrypoint (Debian-based image)
# Exports env vars so cron jobs inherit them, then starts cron in foreground.

# Write all current env vars to a file that cron jobs can source
# Values are single-quoted so special chars (#, \, !, etc.) are preserved
printenv | sed "s/'/'\\\\''/g; s/=\(.*\)/='\1'/" > /app/.env.docker

# Write crontab: run pipeline daily at 7 AM (container TZ=America/Denver)
echo "0 7 * * * . /app/.env.docker; cd /app && /usr/local/bin/python scripts/pipeline.py --verbose >> /proc/1/fd/1 2>&1" | crontab -

echo "Cron scheduled: pipeline runs daily at 7:00 AM Mountain Time"
crontab -l

# Start cron in foreground
exec cron -f -L 2
