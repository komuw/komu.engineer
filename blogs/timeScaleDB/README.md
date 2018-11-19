run:
```sh
docker-compose up
```    
then watch as collector collects logs, ie:  
```sh
docker-compose logs -f log_collector
```    

The `log_emitter` container is your application that writes/emits logs to a named linux Pipe.         
the `log_collector` is an agent that reads logs from the said named linux pipe and sends them to a `timescaleDB/postgres` container     


##### Linux named pipe/FIFO:   
The linux pipe buffers are implemnted as circular buffers[1].    
A consequence of the circular buffer is that when it is full and a subsequent write is performed:      
  (a) then it starts overwriting the oldest data[2].         

The only difference between pipes and FIFOs is the manner in which they are created and opened.     
Once these tasks have been accomplished, I/O on pipes and FIFOs has exactly the same semantics[3].     

Since Linux 2.6.11, the pipe capacity is 16 pages(65,536bytes ie 65KB).       
The command:     
```sh
  cat /proc/sys/fs/pipe-max-size
  1048576 == 1MB
```
shows the value that acts as a ceiling on the default capacity of a new pipe[3]     
 



##### TODO:   
A. load test.    
B. unit tests     


##### NOTES:
- you cant make one write which is bigger than `PIPE_BUF`[3]     
on linux the size of `PIPE_BUF` is about `4096`    
ie this code is likely to fail    
```python
write_data = write_data.encode() * 4098
os.write(pipe, write_data)
```


##### References:
1. http://www.pixelbeat.org/programming/stdio_buffering/    
2. https://en.wikipedia.org/wiki/Circular_buffer   
3. http://man7.org/linux/man-pages/man7/pipe.7.html      

connect to db:
```sh
export PGPASSFILE=.pgpass && psql --host=localhost --port=5432 --username=myuser --dbname=mydb
```

Our logs will have this structure:
```sh
time                TIMESTAMPTZ       NOT NULL,
application_name    TEXT              NOT NULL,
environment_name    TEXT              NOT NULL,
log_event           TEXT              NOT NULL,
trace_id            TEXT              NOT NULL,
file_path           TEXT              NOT NULL,
host_ip             TEXT              NOT NULL,
data                JSONB             NULL
```
connect to db and insert sample data:
```sql
INSERT INTO logs(time, application_name, environment_name, log_event, trace_id, file_path, host_ip, data)
  VALUES
    (NOW(), 'WebApp', 'production', 'login', '0ad94512-df55-11e8-9805-5b8e82d370a6', '/usr/src/app/login.py', '127.0.0.1', '{"user": "Shawn Corey Carter", "age": 48, "email": "someemail@email.com"}');
```
you can also do bulk inserts, they perform better:
```sql
INSERT INTO logs(time, application_name, environment_name, log_event, trace_id, file_path, host_ip, data)
  VALUES
    (NOW(), 'LoadBalancer', 'production', 'access', 'cc47066c-df5f-11e8-93a0-03a5cafa053b', '/usr/src/app/haproxy', '127.0.0.1', NULL),
    (NOW(), 'WebApp', 'production', 'login', '0ad94512-df55-11e8-9805-5b8e82d370a6', '/usr/src/app/login.py', '127.0.0.1', '{"user": "Shawn Corey Carter", "age": 48, "email": "someemail@email.com"}');
```
then you can query:
```sql
SELECT * FROM logs ORDER BY time DESC LIMIT 5;
SELECT * FROM logs WHERE logs.trace_id = 'bfb95991-ae1b-4f7b-bc11-024dc53b964f';
SELECT * FROM logs WHERE logs.host_ip = '172.18.0.3';
/* where 172.18.0.3 is the containers IP. (see: docker network inspect namedpiper_default) */
```

```sql
/*
find the latest five events where an exception has been raised
*/
SELECT
    log_event,
    trace_id,
    data -> 'error' AS error
FROM
    logs
WHERE
    data -> 'error' IS NOT NULL
ORDER BY
    time DESC
LIMIT 5;
```

```sql
/*
find the path/trace taken by the last request which resulted in an exception occuring.
*/
SELECT
    log_event,
    trace_id,
    file_path,
    data -> 'error' AS error
FROM
    logs
WHERE
    logs.environment_name = 'production'
    AND
    logs.trace_id = (
        SELECT
            trace_id
        FROM
            logs
        WHERE
            data -> 'error' IS NOT NULL
        ORDER BY
            time DESC
        LIMIT 1);
```



```sql
/*
select all instances in which the web application has returned a http 5XX
*/
SELECT
    log_event,
    trace_id,
    data -> 'status_code' AS status_code
FROM
    logs
WHERE
    logs.environment_name = 'production'
    AND
    logs.application_name = 'web_app'
    AND
    data -> 'status_code' IN ('500', '504');
```


```sql
/*
find average, 75th and 99th percentile response time(in milliseconds) of the web application
*/
SELECT
    percentile_disc(0.5) WITHIN GROUP (ORDER BY data -> 'response_time') AS average,
    percentile_disc(0.75) WITHIN GROUP (ORDER BY data -> 'response_time') AS seven_five_percentile,
    percentile_disc(0.99) WITHIN GROUP (ORDER BY data -> 'response_time') AS nine_nine_percentile
FROM
    logs
WHERE
    logs.environment_name = 'canary'
    AND
    logs.application_name = 'web_app'
    AND
    data -> 'status_code' IS NOT NULL
    AND
    data -> 'response_time' IS NOT NULL;
/*
returns:
 average | seven_five_percentile | nine_nine_percentile
---------+-----------------------+----------------------
 56      | 82                    | 110
*/
```