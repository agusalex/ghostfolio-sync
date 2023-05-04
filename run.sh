#!/bin/sh

FILE="$HOME/ghost.lock"
take()
{
  touch "$FILE"
  date > "$FILE"
}

release()
{
  rm "$FILE"
}

if [ ! -f "$FILE" ]; then
   echo "Starting Sync"
   take
   "$VIRTUAL_ENV/bin/python3" main.py
   release
   echo "Finished Sync"
else
   echo "Lock-file present $FILE, try increasing time between runs, next schedule will be $CRON"
fi