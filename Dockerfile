#Deriving the latest base image
FROM python:3.9.16-alpine3.17

RUN apk add git

WORKDIR /usr/app/src
COPY requirements.txt .
RUN pip3 install -r requirements.txt
#ADD https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 /bin/dumb-init
RUN apk add dumb-init
COPY ./entrypoint.sh /root/entrypoint.sh
COPY ./run.sh /root/run.sh
RUN chmod 777 /root/entrypoint.sh /root/run.sh /bin/dumb-init
COPY main.py .
COPY SyncIBKR.py .
ENTRYPOINT ["dumb-init", "--"]
CMD /root/entrypoint.sh | while IFS= read -r line; do printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$line"; done;