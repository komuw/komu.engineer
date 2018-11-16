FROM postgres:11-alpine

# inspiration from https://github.com/timescale/timescaledb-docker
COPY postgres-init.sh /docker-entrypoint-initdb.d/

WORKDIR /usr/src/app
COPY . /usr/src/app

RUN chmod 777 /usr/src/app/tx_deathrow_full.csv
