#!/bin/sh

LOCK_FILE="$HOME/ghost.lock"
HEALTH_FILE="$HOME/ghost.lock"
aquire_lock()
{
  touch "$LOCK_FILE"
  date > "$LOCK_FILE"
}

release_lock()
{
  rm "$LOCK_FILE"
}

do_healthcheck()
{
  local status="$1"
  if ([ -n "$HEALTHCHECK_URL" ] && [ $status -eq 0 ]); then
    wget ${HEALTHCHECK_URL} -O /dev/null;
  fi
}

write_health()
{
    local status="$1"
    if [ $status -eq 0 ]; then
      echo "HEALTHY" > HEALTH_FILE
    else
      echo "DOH!" > HEALTH_FILE
    fi
}

if [ ! -f "$LOCK_FILE" ]; then
   echo "Starting Sync"
   aquire_lock
   "$VIRTUAL_ENV/bin/python3" main.py
   STATUS_CODE=$?
   release_lock
   echo "Finished Sync"
   do_healthcheck $STATUS_CODE
   write_health $STATUS_CODE
   exit $STATUS_CODE
else
   echo "Lock-file present $LOCK_FILE, try increasing time between runs, next schedule will be ${CRON:-never, no cron set}"
fi
