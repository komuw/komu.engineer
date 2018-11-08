#!/usr/bin/env bash
if test "$BASH" = "" || "$BASH" -uc "a=();true \"\${a[@]}\"" 2>/dev/null; then
    # Bash 4.4, Zsh
    set -euo pipefail
else
    # Bash 4.3 and older chokes on empty arrays with set -u.
    set -eo pipefail
fi
shopt -s nullglob globstar



create_db() {
    printf "\n\n
    create_db START \n
    #############\n\n"

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c "CREATE DATABASE myDBname TEMPLATE template1 ENCODING UTF8;"

    printf "\n\n create_db END \n\n"      
}

create_extension() {
    printf "\n\n
    create_extension START \n
    #############\n\n"

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"

    printf "\n\n create_extension END \n\n"      
}


# PostgreSQL stores TIMESTAMPTZ in UTC value.
# When you insert a value into a TIMESTAMPTZ column, PostgreSQL converts the TIMESTAMPTZ value into a UTC value and stores the UTC value in the table.
# When you query timestamptz from the database, PostgreSQL converts the UTC value back to the time value of the timezone set by the database server, the user, or the current database connection.


create_tables() {
    printf "\n\n ###########\n
    create_table START \n
    #############\n\n"

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c '
    CREATE TABLE IF NOT EXISTS myTableName (
        /* constraint names appear in error msgs. */
        time TIMESTAMPTZ CONSTRAINT "constraintName time cant be null" NOT NULL,
        trace_id varchar(40) UNIQUE NOT NULL,
        data JSONB NULL,
        /* The CHECK clause specifies an expression producing a Boolean result. */
        age integer CHECK (age > 0),
        PRIMARY KEY (time, trace_id)
    );'


    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c '
    CREATE TABLE IF NOT EXISTS alasTable (
        /* PRIMARY KEY says that a column/s can contain ONLY unique (non-duplicate), non-NULL values */
        trace_id varchar(40) PRIMARY KEY
    );'

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c '
    CREATE TABLE IF NOT EXISTS okayTable (
            my_id varchar(40),
            /*
            Foreign key is a field/s in a table that uniquely identifies a row in another table.
            What happens to rows in okayTable if a row in alasTable is deleted?
            ON DELETE CASCADE deletes rows in okayTable if corresponding ones in alasTable are deleted.
            theres also an "ON UPDATE action" for what to do to rows on update.
            Note that "my_id" and "trace_id" need to have the same data type
            */
            FOREIGN KEY (my_id) REFERENCES alasTable (trace_id) ON DELETE CASCADE
    );'

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c '
    CREATE TABLE IF NOT EXISTS logs (
        time TIMESTAMPTZ NOT NULL,
        application_name TEXT NOT NULL,
        environment_name TEXT NOT NULL,
        log_event TEXT NOT NULL,
        trace_id TEXT NOT NULL,
        file_path TEXT NOT NULL,
        host_ip TEXT NOT NULL,
        data JSONB NULL,
        PRIMARY KEY (time, trace_id)
    );'

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c '
    CREATE TABLE IF NOT EXISTS executions (
            first_name varchar(140),
            last_name varchar(140),
            ex_number smallint,
            ex_age smallint,
            ex_date date,
            county varchar(80),
            last_statement text
    );'

    printf "\n\n create_table END \n\n"    
}

create_table_indices() {
     printf "\n\n ###########\n
    create_table_indices START \n
    #############\n\n"

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c '
    /* we use DESC so that the most recent appear first.
    You can create different kind of indices: btree, hash, gist, spgist, gin, and brin 
    The default one is btree, gin index may be good for JSONB data 
    see: https://www.postgresql.org/docs/current/datatype-json.html#JSON-INDEXING
    you should prefer JSONB over json
    */
    CREATE INDEX CONCURRENTLY IF NOT EXISTS myTimeIdexName ON logs (time DESC)
    WHERE
        log_event IS NOT NULL AND time IS NOT NULL;'

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c '
    CREATE INDEX CONCURRENTLY IF NOT EXISTS myJsonDataIndexName ON logs
        USING GIN (data)
    WHERE
        data IS NOT NULL;'

    printf "\n\n create_table_indices END \n\n"   
}



run_sanity_check() {
    printf "\n\n ###########\n
    run_sanity_check START: \n
    SELECT * FROM executions;\n\n"

    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c 'SELECT * FROM executions;'

    printf "\n\n run_sanity_check END \n\n"   
}

# call the functions
create_db
# create_extension
create_tables
create_table_indices
run_sanity_check
