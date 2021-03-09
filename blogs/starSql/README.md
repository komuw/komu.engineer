#### About  

This are my notes taken while mostly doing;  
1. https://selectstarsql.com  and also;   
2. https://sqlbolt.com    
3. https://www.techonthenet.com/postgresql/joins.php    
4. http://sqlfiddle.com   
5. https://github.com/darold/pgFormatter     
6. http://sqlformat.darold.net     
7. https://modern-sql.com/video     


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
    application_version    TEXT NOT NULL,
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
Great articles on indices/index:    
1. https://blog.timescale.com/use-composite-indexes-to-speed-up-time-series-queries-sql-8ca2df6b3aaa          

2. https://www.postgresql.org/docs/11/indexes.html       

3. https://docs.timescale.com/v1.0/using-timescaledb/schema-management#indexing-best-practices      




```sql
/*
if your csv has a HEADER line, it is important to add WITH (HEADER)
otherwise you'll get errors lik; invalid input syntax for integer
*/
COPY executions (ex_number,last_name,first_name,ex_age,ex_date,county,last_statement) FROM '/usr/src/app/tx_deathrow_full.csv' WITH (FORMAT csv, HEADER);
```


## chapter 1: Beazley last statement(selecting)
The way select works is like;
```sql
/* 
multi-line comment
*/
-- single-line comment.
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
/*
that query returns Beazley's last statement
*/
```

## chapter 2: claims of innocennce(aggregate funcs)
```sql
/*
to find the count of inmates who didnt provide a last_statement
*/
select count(*)
from executions
where last_statement is not null;
/*
you do not use equality operators(=,<) for null.
instead u use is null, or is not null
*/
```

```sql
SELECT COUNT(*) FROM executions;
/*
this finds the total number of executions
*/
```

```sql
/* min, max, avg age of exuctions*/
SELECT MIN(ex_age), MAX(ex_age), AVG(ex_age)
FROM executions;
```

```sql
/*
99th percentile age of execution
*/
SELECT percentile_disc(0.99) 
WITHIN GROUP (ORDER BY ex_age) 
FROM executions;
```

```sql
/*
list all counties without dupliation
*/
SELECT DISTINCT county 
FROM executions;
```

```sql
CASE 
      WHEN condition_1  THEN result_1
     WHEN condition_2  THEN result_2
     [WHEN ...]
     [ELSE result_n]
END
/*
A CASE block is like an IF/THEN/ELSE clause in other programming languages.
each condition(condition_1, condition_2 etc) is an expression that returns a boolean value, either true or false.
If the condition evaluates to true, it returns the result which follows the condition, and all other CASE branches do not process at all.

If all conditions evaluate to false, the CASE expression will return the result in the ELSE(ie result_n) part. 
If you omit the ELSE clause, the CASE expression will return null.
*/
```

```sql
/*
find the number of inmates who were age 25 or lower at time of execution
and also the number of inmates who were age 25 or higher at time of execution
*/
SELECT
    SUM(
        CASE WHEN ex_age <= 25 THEN
            1
        ELSE
            0
        END) AS "young",
    SUM(
        CASE WHEN ex_age > 25 THEN
            1
        ELSE
            0
        END) AS "old"
FROM
    executions;
/*
returns;
 young | old
-------+-----
     6 | 547
*/
```


```sql
/*
find number of people who claimed to have been innocent in their last_statements
*/
select
   sum(
       case when last_statement like '%innocent%' then
           1
       else
           0
        end) as innocent
FROM
    executions;
/*
returns:
innocent
----------
       31
*/
```


```sql
/*
Find a count of all inmates
and also a count of inmates who claim to have been innocent.
We are multiplying by 1.0 so that we can be able to do float division later on.
*/
select
   sum(
       case when last_statement like '%innocent%' then
           1
       else
           0
        end) as innocent,
   count(
   *
   ) * 1.0 as all_inmates
FROM
    executions;
/*
returns:
 innocent | all_inmates
----------+-------------
       31 |       553.0
*/
```


```sql
/*
Find the proportion of inmates with claims of innocence in their last statements.
NB:
- we multiply by 1.0 so that we can be able to do float division later on.
- it is easier to do the division if the multipliation
is in the first part as opposed to been in the second part as in the prev sql query.
*/
select
   sum(
       case when last_statement like '%innocent%' then
           1
       else
           0
        end) * 1.0 
    /
    count(
        *
     ) as proportion_innocent
FROM
    executions;
/*
returns:
  proportion_innocent
------------------------
 0.05605786618444846293
*/
```



```sql
/*
percentage of inmates who claimed to be innocent in their last_statements.
*/
select
   (
       sum(
            case when last_statement like '%innocent%' then
                1
            else
                0
            end
        ) * 1.0 

        -- division
        /

        count(
            *
        )
    ) *100 as percent_innocent
FROM
    executions;
/*
returns:
    percent_innocent
------------------------
 5.60578661844484629300
*/
```



## chapter 3: the long tail.
**GROUP BY** allows us to split up the dataset and apply aggregate functions within each group, resulting in one row per group.  
It comes after the **WHERE** block.   
Implicitly, you should only need to use this when you have aggregate functions in your query.    
```sql
/*
execution counts by/per county

In the SELECT block, <expression> AS <alias> 
provides an alias that can be referred to later in the query. 
*/
SELECT
    county,
    COUNT(*) AS county_executions
FROM
    executions
GROUP BY
    county;
/*
returns:
    county    | county_executions 
--------------+-------------------
 Hamilton     |                 1
 Bowie        |                 5
*/
```

```sql
/*
number of executions(that did not have a last statement) from each county.
*/
SELECT
    county,
    last_statement IS NOT NULL AS has_last_statement,
    COUNT(*)
FROM
    executions
GROUP BY
    county,
    has_last_statement;
/*
returns:
county    | has_last_statement | count 
--------------+--------------------+-------
 Houston      | t                  |     1
 Bee          | t                  |     2
 Crockett     | t                  |     1
 Lubbock      | t                  |    12
*/
```


```sql
/*
Count the number of inmates aged 50 or older that were executed in each county.
*/
SELECT
    ex_age,
    ex_age >= 50 AS BooleanIsOlderThanFifty,
    count(*)
FROM
    executions
WHERE
    BooleanIsOlderThanFifty = true
GROUP BY
    county,
    BooleanIsOlderThanFifty;
/*
DOES NOT WORK.
you would think that the above will work, but it does not.
This is because the WHERE block is EVALUATED BEFORE the SELECT block.
So you cannot use things that are returned from select block in where block,
But YOU CAN use things returned from SELECT block in GROUP BY block.
*/
```

```sql
/*
CORRECT:
Count the number of inmates aged 50 or older that were executed in each county.
*/
SELECT
    county,
    COUNT(*)
FROM
    executions
WHERE
    ex_age >= 50
GROUP BY
    county;
```



```sql
/*
List the counties in which more than 2 inmates aged 50 or older have been executed.
*/
SELECT
    county,
    count(*) AS num_executions
FROM
    executions
WHERE
    ex_age >= 50
GROUP BY
    county
HAVING
    -- we cant use num_executions here
    count(*) > 2;
/*
returns:
   county   | num_executions 
------------+----------------
 Harris     |             21
 Tarrant    |              4

note we cant use num_executions in the having block,
we are force to repeat  count(*)
*/
```


```sql
/*
This query finds the number of inmates from each county and 10 year age range.
*/
SELECT
    county,
    ex_age / 10 AS decade_age,
    COUNT(*)
FROM
    executions
GROUP BY
    -- u can use decade_age from select in group by
    county, decade_age;
```

##### Nested queries
```sql
/*
Find the names of the inmate who had the longest last_statement.
*/
SELECT
    first_name,
    last_name
FROM
    executions
WHERE
    LENGTH(last_statement) = (
        SELECT
            MAX(LENGTH(last_statement))
        FROM
            executions);
```



```sql
/*
Query to find the percentage of executions from each county.
*/
SELECT
    county,
    -- we want decimal percentages
    100.0 * COUNT(*)
        / 
        (
            SELECT
                count(*)
            FROM
                executions
        ) AS percentage
FROM
    executions
GROUP BY
    county
ORDER BY
    percentage DESC;
/*
returns:
    county    |       percentage       
--------------+------------------------
 Harris       |    23.1464737793851718
 Dallas       |    10.4882459312839060
 Bexar        |     8.3182640144665461
 Tarrant      |     7.4141048824593128
*/
```

## chapter 4: Execution Hiatuses(JOINS)  
There have been several extended periods when no executions took place.   
Our goal is to figure out exactly when they were and research their causes.   

Let's take a detour:   
The big idea behind `JOINs` is to create an augmented table because the original doesn't contain the information we need.    
This is a powerful concept because it frees us from the limitations of a single table and allows us to combine multiple tables in potentially complex ways.   

PostgreSQL JOINS are used to retrieve data from multiple tables. - https://www.techonthenet.com/postgresql/joins.php    
The 4types of joins we will look at are: 
- INNER JOIN (or sometimes called simple join)    
- LEFT OUTER JOIN (or sometimes called LEFT JOIN)   
- RIGHT OUTER JOIN (or sometimes called RIGHT JOIN)   
- FULL OUTER JOIN (or sometimes called FULL JOIN)     


1. inner join  
```sql
/*
inner join return all rows from multiple tables where the join condition is met
*/
SELECT columns
FROM table1 
INNER JOIN table2
-- ON <condition> where condition is any statement that can evaluate to true/false
ON table1.column = table2.column;
```
![inner join image](imgs/inner_join.gif)    


2. left outer join    
```sql
/*
left outer join returns the all records from table1 and only those records from table2 that intersect with table1 (ie join condition is met). 
it returns null for the columns in table2 where condition is not met.
*/
SELECT columns
FROM table1
LEFT OUTER JOIN table2
ON <condition>;
```
![left outer join image](imgs/left_outer_join.gif)  


3. right outer join    
```sql
/*
it returns null for the columns in table1 where condition is not met.
*/
SELECT columns
FROM table1
RIGHT OUTER JOIN table2
ON table1.column = table2.column;
```
![right outer join image](imgs/right_outer_join.gif)   


4. full outer join   
```sql
/*
full outer join returns all rows from the LEFT-hand table and RIGHT-hand table with nulls in place where the join condition is not met.
*/
SELECT columns
FROM table1
FULL OUTER JOIN table2
ON table1.column = table2.column;
```
![full outer join image](imgs/full_outer_join.gif)     


5. self join   
This is not really a new join type on it's own, rather it is an application of JOIN on the same table.   
You can apply any of the above 4 join types to one table.
```sql
SELECT column/s
FROM myTableName table1
INNER JOIN myTableName table2 
ON table1.columnName = table2.otherColumn;
```
As an example, (the example is nonsensical but it works);
```sql
SELECT
    table1.first_name,
    table1.ex_number,
    table2.ex_age
FROM
    executions table1
INNER JOIN executions table2
ON table1.ex_number = table2.ex_age;
/*
returns:
 first_name | ex_number | ex_age 
------------+-----------+--------
 Jerome     |        34 |     34
 Ruben      |        66 |     66
 Mikel      |        37 |     37
*/
```   
End of detour.    


```sql
/*
find the gaps(hiatuses) in executions.
*/
SELECT
    table1.first_name AS t1_fname,
    table2.first_name AS t2_fname,
    table1.ex_number AS t1_ex_num,
    table2.ex_number AS t2_ex_num,
    table1.ex_date AS t1_ex_date,
    table2.ex_date AS t2_ex_date,
    table1.ex_date - table2.ex_date AS day_difference
FROM
    executions table1
INNER JOIN executions table2 
ON table1.ex_number = table2.ex_number + 1
ORDER BY
    day_difference DESC
LIMIT 12;
/*
returns:
 t1_fname |   t2_fname   | t1_ex_num | t2_ex_num | t1_ex_date | t2_ex_date | day_difference 
----------+--------------+-----------+-----------+------------+------------+----------------
 James    | Charlie      |         2 |         1 | 1984-03-14 | 1982-12-07 |            463
 Donald   | Robert       |        28 |        27 | 1988-11-03 | 1988-01-07 |            301
*/
```

Alternatively; 
```sql
/*
find the gaps(hiatuses) in executions.
*/
SELECT
    current.ex_number AS cur_ex_num,
    previous.ex_number AS prev_ex_num,
    current.ex_date AS cur_ex_date,
    previous.ex_date AS prev_ex_date,
    current.ex_date - previous.ex_date AS day_difference
FROM
    executions current
INNER JOIN executions previous 
ON current.ex_number = previous.ex_number + 1
ORDER BY
    day_difference DESC
LIMIT 12;
/*
returns:
 cur_ex_num | prev_ex_num | cur_ex_date | prev_ex_date | day_difference 
------------+-------------+-------------+--------------+----------------
          2 |           1 | 1984-03-14  | 1982-12-07   |            463
         28 |          27 | 1988-11-03  | 1988-01-07   |            301
        406 |         405 | 2008-06-11  | 2007-09-25   |            260
*/
```    

The big idea behind `JOINs` has been to create an augmented table because the original didn’t contain the information we needed.    
This is a powerful concept because it frees us from the limitations of a single table and allows us to combine multiple tables in potentially complex ways.   


## chapter 5: Anatomy and order of execution
```sql
/*
anantomy of an SQL query.
*/
SELECT
    column_name (s)
FROM
    table_name
WHERE
    condition
GROUP BY
    column_name (s)
HAVING
    condition
ORDER BY
    column_name (s);
```


alternatively
```sql
/*
anantomy of an SQL query.
*/
SELECT
    column_name (s), AGG_FUNC(column_or_expression),
FROM
    table_name1
  INNER JOIN table_name2
    ON condition
WHERE
    condition
GROUP BY
    column_name (s)
HAVING
    condition
ORDER BY
    column_name (s) ASC/DESC
LIMIT X OFFSET Y;
```

The order of SQL query execution is: https://sqlbolt.com/lesson/select_queries_order_of_execution,  

1. `FROM and JOINs`  
they are executed first to determine the total working set of data.   
2. `WHERE`  
WHERE constraints are applied to the individual rows.  
Aliases in the SELECT part of the query are not accessible.  
3. `GROUP BY`   
Implicitly, you should only need to use this when you have aggregate functions in your query.  
4. `HAVING`   
Like the `WHERE` clause, aliases are also not accessible from this.     
5. `SELECT`  
Any expressions in the SELECT part of the query are finally computed.    
6. `DISTINCT`    
Of the remaining rows, rows with duplicate values in the column marked as DISTINCT will be discarded.    
7. `ORDER BY`  
If an order is specified by the ORDER BY clause, the rows are then sorted by the specified data in either ascending or descending order.    
Since all the expressions in the SELECT part of the query have been computed, you **CAN** reference **aliases** in this clause.   
8. `LIMIT / OFFSET`   
Finally, the rows that fall outside the range specified by the LIMIT and OFFSET are discarded, leaving the final set of rows to be returned from the query.    



## chapter 6: WITH BLOCK(common table expression/CTE)    
It solves(among others) the problem of nested queries - https://modern-sql.com/video(starting at the 3:30 mark)    
Lets say we wanted to answer the question:     
`Find all counties that have executed people who are older than 60yrs AND
the name of the county ends in 'on'`      

The first half of the query can be answered by the query:   
```sql
/*
select all counties which have had
executions of people older than 60
*/
SELECT DISTINCT
    county
FROM
    executions
WHERE
    ex_age >60;
/*
returns 9 counties
   county
-------------
 Harris
 Lee
 Tarrant
*/
```

However to answe the full question, we may have to use nested queries in the FROM block:     
```sql
/*
select all counties which have had executions
of people older than 60 and their names ends in 'on'
*/
SELECT
    *
FROM (
    SELECT DISTINCT
        county
    FROM
        executions
    WHERE
        ex_age > 60
    ) AS counties_killing_seniors
WHERE
    county LIKE '%on';
/*
returns 2 counties
  county
-----------
 Grayson
 Henderson
*/
```     


This can also be solved using `WITH` clause;    
```sql
WITH query_name (column_name1, ...) AS
     (SELECT ...),
     another_query_name (some_column, ...) AS
     (SELECT ...)
     
SELECT ...
```
This query (and subqueries it contains) can refer to the just defined query name in their FROM clause. - https://modern-sql.com/feature/with      
ie we can refer to `query_name` inside the FROM of the main SELECT or inside the subqueries themselves.    
**NB:** WITH queries are **ONLY** visible in the SELECT they precede.     


So, our previous query re-implemented using `WITH`:   
```sql
/*
select all counties which have had executions
of people older than 60 and their names ends in 'on'
*/
WITH counties_killing_seniors AS 
(
    SELECT DISTINCT
        county
    FROM
        executions
    WHERE
        ex_age > 60
)
SELECT
    *
FROM
    counties_killing_seniors
WHERE
    county LIKE '%on';
/*
returns:
  county
-----------
 Grayson
 Henderson
(2 rows)
*/
```

So, which of the two is faster?    
Let's benchmark:   
```sql
SET statement_timeout TO '10s';

DO $$
DECLARE
  v_ts TIMESTAMP;
  v_repeat CONSTANT INT := 10000;
  rec RECORD;
BEGIN
 
  -- Repeat the whole benchmark several times to avoid warmup penalty
  FOR i IN 1..5 LOOP
    v_ts := clock_timestamp();
 
    FOR i IN 1..v_repeat LOOP
      FOR rec IN (
        SELECT
            *
        FROM (
            SELECT DISTINCT
                county
            FROM
                executions
            WHERE
                ex_age > 60
            ) AS counties_killing_seniors
        WHERE
            county LIKE '%on'
      ) LOOP
        NULL;
      END LOOP;
    END LOOP;
 
    RAISE INFO 'Run %, subquery statement: %', i, (clock_timestamp() - v_ts); 
    v_ts := clock_timestamp();
 
    FOR i IN 1..v_repeat LOOP
      FOR rec IN (
        WITH counties_killing_seniors AS 
        (
            SELECT DISTINCT
                county
            FROM
                executions
            WHERE
                ex_age > 60
        )
        SELECT
            *
        FROM
            counties_killing_seniors
        WHERE
            county LIKE '%on'
      ) LOOP
        NULL;
      END LOOP;
    END LOOP;
 
    RAISE INFO 'Run %, with clause statement: %', i, (clock_timestamp() - v_ts); 
  END LOOP;
END$$;
/*
returns:
INFO:  Run 1, subquery statement: 00:00:00.569954
INFO:  Run 1, with clause statement: 00:00:00.555335
INFO:  Run 2, subquery statement: 00:00:00.560441
INFO:  Run 2, with clause statement: 00:00:00.545877
INFO:  Run 3, subquery statement: 00:00:00.55699
INFO:  Run 3, with clause statement: 00:00:00.585253
INFO:  Run 4, subquery statement: 00:00:00.608103
INFO:  Run 4, with clause statement: 00:00:00.568079
INFO:  Run 5, subquery statement: 00:00:00.555735
INFO:  Run 5, with clause statement: 00:00:00.557055
*/
```
Both of them are on par.    
You should benchmark to see if one is slower than another by a huge margin.    
It has been suggested that in some versions of postgres, `WITH`/CTE might be slow; see: https://blog.2ndquadrant.com/postgresql-ctes-are-optimization-fences/    
benchmark!    

## chapter 7: postgres tidbits   
1. You should set an application_name for your queries.    
By explicitly marking each connection you open with `application_name`, you’ll be able to track what your application is doing at a glance:   
```sql
SET application_name TO 'web.production';
```
```sql
SELECT application_name, COUNT(*) FROM pg_stat_activity GROUP BY application_name;
/*
returns:
 application_name | count
------------------+-------
                  |     5
 web.production   |     1
*/
```    

2. You should set a statement timeout.   
Long running queries can have an impact on your database performance because they may hold locks or over-consume resources.    
Postgres allows you to set a timeout per connection that will abort any queries exceeding the specified value.   
```sql
SET statement_timeout TO '10s';
```

3. You should track the sources of your queries.    
Being able to determine which part of your code is executing a query makes optimization easier, and easier to track down.      

**NB:** The `pg_stat_statements` extension needs to be installed first.     
You can check if it is installed via(the `installed_version` column should not be null if installed):  
```sql
SELECT * 
FROM
    pg_available_extensions 
WHERE 
    name LIKE 'pg%';
```

Then,  
```sql
SELECT first_name, county FROM executions; -- /usr/app/views.py:47
```
and checking stats:
```sql
SELECT
    (total_time/sum(total_time) OVER()) * 100 AS exec_time, calls, query
FROM
    pg_stat_statements
ORDER BY
    total_time DESC LIMIT 10;
/*
returns:
exec_time | 12.2119460729825
calls     | 7257
query     | SELECT first_name, county FROM executions; -- /usr/app/views.py:47
*/
```


4. check table sizes/index sizes
```sql
SELECT *, pg_size_pretty(total_bytes) AS total
    , pg_size_pretty(index_bytes) AS INDEX
    , pg_size_pretty(toast_bytes) AS toast
    , pg_size_pretty(table_bytes) AS TABLE
  FROM (
  SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes FROM (
      SELECT c.oid,nspname AS table_schema, relname AS TABLE_NAME
              , c.reltuples AS row_estimate
              , pg_total_relation_size(c.oid) AS total_bytes
              , pg_indexes_size(c.oid) AS index_bytes
              , pg_total_relation_size(reltoastrelid) AS toast_bytes
          FROM pg_class c
          LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE relkind = 'r'
  ) a
) a;
```   

5. automate index creation   
It is hard to know ahead of time which indices are important to create.    
What indices should we create that will speed up 99% of all our queries?   
There are two ways we could do it;    
- Use [hypopg](https://hypopg.readthedocs.io/en/latest/) which is a tool that can create hypothetical indices.   
A hypothetical/virtual, index is one that doesn’t really exists, and thus doesn’t cost CPU, disk or any resource to create.   
They’re useful to know if specific indexes can increase performance for problematic queries, since you can know if PostgreSQL will use these indexes or not without having to spend resources to create them.    
- Index [all the things](https://www.citusdata.com/blog/2017/10/11/index-all-the-things-in-postgres/), measure which ones are actually used by your queries, the eliminate the ones that aren't used. See linked article.    
Also see this talk, [how postgres could index itself](https://www.youtube.com/watch?v=Mni_1yTaNbE)      

- You could use BRIN indices for performance and also reduced index sizes.    
https://info.crunchydata.com/blog/postgresql-brin-indexes-big-data-performance-with-minimal-storage      


6. tune Autovacuum     
- https://www.2ndquadrant.com/en/blog/autovacuum-tuning-basics/     
- https://gist.github.com/oguya/57e6bcbacc27e96eaddb6b5f95ebfe31 - cool autovacuum notes by @oguya


7. find number of dead tuples/rows and last time autovacuum ran on tables
```sql
SELECT
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    last_autoanalyze,
    last_autovacuum
FROM
    pg_stat_all_tables
ORDER BY
    n_dead_tup / (n_live_tup * current_setting('autovacuum_vacuum_scale_factor')::float8 + current_setting('autovacuum_vacuum_threshold')::float8)
    DESC
LIMIT 10;
```
```sh
schemaname |     relname     | n_live_tup | n_dead_tup |        last_autovacuum
------------+-----------------+------------+------------+-------------------------------
 public     | mine_cool      |        172 |       2094 | 2019-09-17 05:36:29.139304+00
 ```
 
 8. Find unused indexes(you can then go ahead and delete them)
```sql
-- https://hakibenita.com/postgresql-unused-index-size
SELECT
    relname,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelname::regclass)) as size
FROM
    pg_stat_all_indexes
WHERE
    schemaname = 'public'
    AND indexrelname NOT LIKE 'pg_toast_%'
    AND idx_scan = 0
    AND idx_tup_read = 0
    AND idx_tup_fetch = 0
ORDER BY
    size DESC;
```

9. Identify invalid indexes that were created during index rebuild(you can then delete them)
```sql
-- https://hakibenita.com/postgresql-unused-index-size
SELECT
    c.relname as index_name,
    pg_size_pretty(pg_relation_size(c.oid))
FROM
    pg_index i
    JOIN pg_class c ON i.indexrelid = c.oid
WHERE
    -- New index built using REINDEX CONCURRENTLY
    c.relname LIKE  '%_ccnew'
    -- In INVALID state
    AND NOT indisvalid
LIMIT 10;
```

10. Find indexed columns with high null_frac. ie indices that index both non-NULL and also NULL items    
Once you find them, change the index to be conditional on non-NULL(read the top of this document to see how to do that)
```sql
-- https://hakibenita.com/postgresql-unused-index-size
SELECT
    c.oid,
    c.relname AS index,
    pg_size_pretty(pg_relation_size(c.oid)) AS index_size,
    i.indisunique AS unique,
    a.attname AS indexed_column,
    CASE s.null_frac
        WHEN 0 THEN ''
        ELSE to_char(s.null_frac * 100, '999.00%')
    END AS null_frac,
    pg_size_pretty((pg_relation_size(c.oid) * s.null_frac)::bigint) AS expected_saving
    -- Uncomment to include the index definition
    --, ixs.indexdef
FROM
    pg_class c
    JOIN pg_index i ON i.indexrelid = c.oid
    JOIN pg_attribute a ON a.attrelid = c.oid
    JOIN pg_class c_table ON c_table.oid = i.indrelid
    JOIN pg_indexes ixs ON c.relname = ixs.indexname
    LEFT JOIN pg_stats s ON s.tablename = c_table.relname AND a.attname = s.attname

WHERE
    -- Primary key cannot be partial
    NOT i.indisprimary

    -- Exclude already partial indexes
    AND i.indpred IS NULL

    -- Exclude composite indexes
    AND array_length(i.indkey, 1) = 1

    -- Larger than 10MB
    AND pg_relation_size(c.oid) > 10 * 1024 ^ 2

ORDER BY
    pg_relation_size(c.oid) * s.null_frac DESC;
```

11. Tool that parses EXPLAIN ANALYZE and surfaces recommendations to improve performance 
    https://www.pgmustard.com/
