#!/bin/sh

FILE="$HOME/ghost.lock"
aquire_lock()
{
  touch "$FILE"
  date > "$FILE"
}

release_lock()
{
  rm "$FILE"
}

do_healthcheck()
{
  local status="$1"
  if ([ -n "$HEALTHCHECK_URL" ] && [ $status -eq 0 ]); then
    curl ${HEALTHCHECK_URL} > /dev/null; 
  fi
}

if [ ! -f "$FILE" ]; then
   echo "Starting Sync"
   aquire_lock
   "$VIRTUAL_ENV/bin/python3" main.py
   STATUS_CODE=$?
   release_lock
   echo "Finished Sync"
   do_healthcheck $STATUS_CODE
   exit $STATUS_CODE
else
   echo "Lock-file present $FILE, try increasing time between runs, next schedule will be ${CRON:-never, no cron set}"
fi
