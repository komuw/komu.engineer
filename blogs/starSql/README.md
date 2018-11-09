#### About  

This are my notes taken while mostly doing; https://selectstarsql.com/frontmatter.html   
and also; https://sqlbolt.com/

connect to the db like;   
```sh
export PGPASSFILE=.pgpass && psql --host=localhost --port=5432 --username=myuser --dbname=myDBname
```

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
        theres also an "ON UPDATE action" for what to do to rows on update.
        Note that "my_id" and "trace_id" need to have the same data type
        */
        FOREIGN KEY (my_id) REFERENCES alasTable (trace_id) ON DELETE CASCADE
);

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
);


CREATE TABLE IF NOT EXISTS executions (
     first_name	varchar(140),
     last_name	varchar(140),
     ex_number	smallint,
     ex_age	smallint,
     ex_date	date,
     county	varchar(80),
     last_statement text
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

```sql
/*
if your csv has a HEADER line, it is important to add WITH (HEADER)
otherwise you'll get errors lik; invalid input syntax for integer
*/
COPY executions (ex_number,last_name,first_name,ex_age,ex_date,county,last_statement) FROM '/usr/src/app/tx_deathrow_full.csv' WITH (FORMAT csv, HEADER);
```


## chapter 1: Beazley last statement
The way select works is like;
```sql
/* comment */
SELECT * FROM executions LIMIT 3;
```
```sql
SELECT <column>, <column>, ....
```
```sql
SELECT 50 /2, 51 / 2.0;
/*
SQL does integer division by default. Unless one of the numbers is a float.
returns:
?column? |      ?column?
----------+---------------------
       25 | 25.5000000000000000
*/
```

```sql
/* 
the synatx of the WHERE block is;
  WHERE <clause>
wherein <clause> refers to a Boolean statement
that the computer can evaluate to be true or false 
*/
select first_name, last_name 
from executions
where ex_age <= 25;
/*
in this example we found all inmates who were age 25 or younger
at the time of their execution.
NB: it is <= but not =<
*/
```

```sql
/*
there is also a LIKE <clause>. This allows us to use 
wildcards such as % and _ to match characters. 

'%roy' will return true for rows with first names ‘roy’, ‘Troy’, and ‘Deroy’ but not ‘royman’.
the `_` wildcard on the other hand matches only a single character.
*/
SELECT first_name, last_name, ex_number
FROM executions
WHERE first_name LIKE '_ay____';
/*
returns:
 first_name |  last_name  | ex_number
------------+-------------+-----------
 Gayland    | Bradford    |       468
 Raymond    | Landry, Sr. |        29
 Raymond    | Jones       |       186
 Raymond    | Kinnamon    |        85

ie; first_names that start with ANY character followed by `ay` followed by any OTHER four characters.
*/
```

```sql
/*
complex <clauses> can be made out of simple ones using Boolean operators like NOT, AND and OR.
SQL gives most precedence to NOT and then AND and finally OR. 
You can use parantheses to clarify the order that u want.
*/
SELECT last_statement
FROM executions
WHERE first_name = 'Napoleon'
AND last_name = 'Beazley';
```