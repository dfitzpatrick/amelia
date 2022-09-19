FROM python:3.10-alpine
RUN apk add --no-cache linux-headers && \
    apk --no-cache add gcc musl-dev && \
    apk --no-cache add postgresql-dev && \
    apk --no-cache add postgresql-libs && \
    apk --no-cache add libc-dev && \
    apk --no-cache add libffi-dev && \
    apk --no-cache add git && \
    apk --no-cache add cmake && \
    apk update

RUN /usr/local/bin/python3.10 -m pip install --upgrade pip

WORKDIR /home/bot
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR /home
RUN pip install --no-cache-dir -e git+https://github.com/dfitzpatrick/ameliapg.git#egg=ameliapg

WORKDIR /home/bot

COPY . .
