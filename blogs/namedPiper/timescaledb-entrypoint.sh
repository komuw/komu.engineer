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


create_table() {
    printf "\n\n ###########\n
    create_table START \n
    #############\n\n"

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c "CREATE TABLE logs (
    time                TIMESTAMPTZ       NOT NULL,
    application_name    TEXT              NOT NULL,
    environment_name    TEXT              NOT NULL,
    log_event           TEXT              NOT NULL,
    trace_id            TEXT              NOT NULL,
    file_path           TEXT              NOT NULL,
    host_ip             TEXT              NOT NULL,
    data                JSONB             NULL
    );"

    # you may want to index the json field
    # see: https://docs.timescale.com/v1.0/using-timescaledb/schema-management#indexing-all-json
    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c "CREATE INDEX idxgin ON logs USING GIN (data);"

    printf "\n\n create_table END \n\n"    
}
create_table
