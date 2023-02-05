#!/bin/sh

rm -f /root/ghost.lock
echo "Starting ghostfolio-sync Docker..."
if [ -z "$CRON" ]; then
  echo "Crontab Not Present running one time now"
  python main.py
else
  echo "$CRON /root/run.sh" > /etc/crontabs/root;
  echo "Next run will be scheduled by the following cron $CRON"
  crond -f -d 8;
fi