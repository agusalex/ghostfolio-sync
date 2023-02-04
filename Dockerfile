#Deriving the latest base image
FROM python:latest


WORKDIR /usr/app/src
COPY main.py .

CMD [ "python", "./main.py"]
