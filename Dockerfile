#Deriving the latest base image
FROM python:3.9.16-alpine3.17

RUN apk add git

WORKDIR /usr/app/src
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY main.py .
CMD [ "python", "./main.py"]
