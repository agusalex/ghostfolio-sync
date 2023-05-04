#!/bin/sh

single_run(){
    echo "Crontab Not Present running one time now"
    sh run.sh
}

cron_run(){
  mkdir -p "$HOME/crontabs"
  echo "$CRON /bin/sh $PWD/run.sh" > "$HOME/crontabs/$USER";
  echo "Next run will be scheduled by the following cron: $CRON"
  supercronic "$HOME/crontabs/$USER"
}

USER=$(whoami)
cd "$HOME" || (echo "my home is no open for me" && exit)
echo "Starting ghostfolio-sync Docker..."

if [ -z "$CRON" ]; then
  single_run
else
  cron_run
fi