FROM python:3.7.7-alpine3.11

WORKDIR /app

COPY requirements.txt .

RUN apk add postgresql-libs \
 && apk add --virtual .build-deps build-base musl-dev postgresql-dev \
 && pip install -r requirements.txt --no-cache-dir \
 && apk --purge del .build-deps

COPY src ./src
COPY config/ config/

CMD python ./src/main.py
