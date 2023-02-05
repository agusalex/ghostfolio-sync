#!/bin/sh

FILE=/root/ghost.lock

if [ ! -f "$FILE" ]; then
   touch $FILE
   echo "Starting Sync"
   cd /usr/app/src || exit
   python main.py
   rm $FILE
   echo "Finished Sync"
else
   echo "Lock-file present $FILE, try increasing time between runs, next schedule will be $CRON"
fi