FROM python:3.12-alpine

LABEL maintainer="Jordan Matelsky <goosepaper@matelsky.com>"
LABEL authors="Sergio Moura <sergio@moura.ca>"

RUN apk --update --no-cache add cairo gdk-pixbuf libffi libjpeg-turbo libstdc++ \
    libxml2 libxslt pango ttf-dejavu

WORKDIR /app
COPY . .
RUN apk add --no-cache --virtual .build-deps build-base git libxml2-dev libxslt-dev libffi-dev \
    libjpeg-turbo-dev python3-dev && \
    pip install uv && \
    uv sync --frozen --no-dev --no-editable && \
    apk del .build-deps && \
    rm -Rf /root/.cache

ENTRYPOINT ["/app/.venv/bin/goosepaper"]
