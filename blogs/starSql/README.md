#### About  

This are my notes taken while mostly doing; https://selectstarsql.com/frontmatter.html   
and also; https://sqlbolt.com/

Note:
1. the commands in here can be ran via psql 
```sql
psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c "CREATE blah blah;"
```
In fact, you can add the command to a bash file that will then be ran at postgres start
see: https://github.com/timescale/timescaledb-docker/blob/681ec4cb7fdc89b126df8eafe983c8db1a143df0/Dockerfile#L8-L9

2. sql formatting is via: https://github.com/darold/pgFormatter

1. create db
```sql
/* u can query to see existing databases
select * from pg_database; */
CREATE DATABASE myDBname TEMPLATE template1 ENCODING UTF8;
```

2. create extension
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

3. create table
```sql
CREATE TABLE IF NOT EXISTS myTableName (
        /* constraint names appear in error msgs. */
        time TIMESTAMPTZ CONSTRAINT "constraintName time cant be null" NOT NULL,
        trace_id varchar(40) UNIQUE NOT NULL,
        data JSONB NULL,
        /* The CHECK clause specifies an expression producing a Boolean result. */
        age integer CHECK (age > 0),
        PRIMARY KEY (time, trace_id)
);

CREATE TABLE IF NOT EXISTS alasTable (
        /* PRIMARY KEY says that a column/s can contain ONLY unique (non-duplicate), non-NULL values */
        trace_id varchar(40) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS okayTable (
        my_id varchar(40),
        /*
         Foreign key is a field/s in a table that uniquely identifies a row in another table.
         What happens to rows in okayTable if a row in alasTable is deleted?
         ON DELETE CASCADE deletes rows in okayTable if corresponding ones in alasTable are deleted.
         there's also an `ON UPDATE action` for what to do to rows on update.
         Note that `my_id` and `trace_id` need to have the same data type
         */
        FOREIGN KEY (my_id) REFERENCES alasTable (trace_id) ON DELETE CASCADE
);

CREATE TABLE logs (
      time TIMESTAMPTZ NOT NULL,
      application_name TEXT NOT NULL,
      environment_name TEXT NOT NULL,
      log_event TEXT NOT NULL,
      trace_id TEXT NOT NULL,
      file_path TEXT NOT NULL,
      host_ip TEXT NOT NULL,
      data JSONB NULL,
      PRIMARY KEY (time, trace_id)
  );
```
The list of postgres data types is at: https://www.postgresql.org/docs/11/datatype.html

4. create index 
```sql
/* we use DESC so that the most recent appear first.
You can create different kind of indices: btree, hash, gist, spgist, gin, and brin 
The default one is btree, gin index may be good for JSONB data 
see: https://www.postgresql.org/docs/current/datatype-json.html#JSON-INDEXING
you should prefer JSONB over json
 */
CREATE INDEX CONCURRENTLY IF NOT EXISTS myTimeIdexName ON logs (time DESC)
WHERE
    log_event IS NOT NULL AND time IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS myJsonDataIndexName ON logs
    USING GIN (data)
WHERE
    data IS NOT NULL;
```