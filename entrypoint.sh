#!/bin/sh

HEALTH_FILE="$HOME/ghost.lock"


single_run(){
    echo "Crontab Not Present running one time now"
    sh run.sh
}

cron_run(){
  mkdir -p "$HOME/crontabs"
  CRON_FILE="$HOME/crontabs/$USER"
  echo "$CRON /bin/sh $HOME/run.sh" > "$CRON_FILE";
  echo "Next run will be scheduled by the following cron: $CRON"
  supercronic "$CRON_FILE"
}

USER=$(whoami)
cd "$HOME" || (echo "my home is no open for me" && exit)
echo "Starting ghostfolio-sync Docker..."

echo "START" >> HEALTH_FILE

if [ -z "$CRON" ]; then
  single_run
else
  cron_run
fi