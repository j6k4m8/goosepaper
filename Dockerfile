FROM alpine:3.18

LABEL maintainer="Jordan Matelsky <goosepaper@matelsky.com>"
LABEL authors="Sergio Moura <sergio@moura.ca>"

RUN apk --update --no-cache add cairo libffi libjpeg libstdc++ libxml2 libxslt pango \
    py3-aiohttp py3-cffi py3-feedparser py3-gobject3 py3-html5lib py3-lxml py3-multidict \
    py3-numpy py3-requests py3-yarl ttf-dejavu

WORKDIR /app
COPY requirements.txt .
RUN apk add --no-cache --virtual .build-deps build-base git libxml2-dev libxslt-dev libffi-dev libjpeg-turbo-dev py3-pip py3-wheel python3-dev && \
    pip3 install -r ./requirements.txt && \
    apk del .build-deps && \
    rm -Rf /root/.cache
COPY . .
RUN apk add --no-cache --virtual .install-deps py3-pip && \
    pip3 install -e . && \
    apk del .install-deps && \
    rm -Rf /root/.cache

ENTRYPOINT ["goosepaper"]
