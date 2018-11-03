#!/usr/bin/env bash
set -eo pipefail


create_extension() {
    printf "\n\n ###########\n
    create_extension START \n
    #############\n\n"

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"

    printf "\n\n create_extension END \n\n"      
}


create_extension
