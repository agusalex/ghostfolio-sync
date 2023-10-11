#Deriving the latest base image
FROM python:3.9.16-alpine3.17

ARG USER=wheel
ARG GROUP=default
ARG UID=1001
ARG GID=1001

ENV HOME /usr/app/src
ENV FILE_WRITE_LOCATION=$HOME/out
ENV TZ=Europe/Bern

# Supercronic stuff
ENV SUPERCRONIC_VERSION="v0.2.26"
ENV SUPERCRONIC_SHA1SUM=7a79496cf8ad899b99a719355d4db27422396735
ENV SUPERCRONIC=supercronic-linux-amd64
ENV SUPERCRONIC_PACKAGE=supercronic-linux-amd64
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/$SUPERCRONIC_VERSION/$SUPERCRONIC_PACKAGE

# dump-init stuff
ENV DUMP_INIT_VERSION="1.2.5"
ADD https://github.com/Yelp/dumb-init/releases/download/v$DUMP_INIT_VERSION/dumb-init_${DUMP_INIT_VERSION}_x86_64 /bin/dumb-init

RUN addgroup --gid $GID $GROUP &&  \
    adduser -S $USER -G $GROUP --uid "$UID" &&  \
    mkdir -p $HOME &&  \
    mkdir -p $FILE_WRITE_LOCATION &&  \
    chown -R $USER:$GROUP $HOME && \
    chown -R $USER:$GROUP $FILE_WRITE_LOCATION && \
    chmod +x /bin/dumb-init && \
    apk update && \
    apk upgrade && \
    apk add --update --no-cache git ca-certificates curl libcap  && \
    # install supercronic
    curl -fsSLO "$SUPERCRONIC_URL" && \
    echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC_PACKAGE}" | sha1sum -c - && \
    chmod +x "${SUPERCRONIC_PACKAGE}" && \
    mv "${SUPERCRONIC_PACKAGE}" "/bin/${SUPERCRONIC_PACKAGE}" && \
    ln -s "/bin/${SUPERCRONIC_PACKAGE}" /bin/supercronic && \
    # remove unwanted deps & cleanup
    apk del --purge ca-certificates curl && \
    rm -rf /tmp/* /var/cache/apk/*

USER $USER
WORKDIR $HOME



COPY --chown=$USER:$GROUP ./entrypoint.sh $HOME/entrypoint.sh
COPY --chown=$USER:$GROUP ./run.sh /$HOME/run.sh
COPY --chown=$USER:$GROUP requirements.txt .
COPY --chown=$USER:$GROUP  *.py $HOME/
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=$HOME/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN chmod 0755 $HOME/entrypoint.sh && \
    chmod 0755 $HOME/run.sh && \
    python3 -m venv $VIRTUAL_ENV && \
    source $VIRTUAL_ENV/bin/activate && \
    $VIRTUAL_ENV/bin/pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT ["dumb-init", "--"]
CMD $HOME/entrypoint.sh | while IFS= read -r line; do printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$line"; done;