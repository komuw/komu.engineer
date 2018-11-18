import os
import json
import asyncio
import asyncpg
import datetime


from logger import getLogger
from batched_logs import batchedLogs


logger = getLogger(name="logs.sender")

logger.info("{}".format({"event": "log_sender_start"}))


IN_DOCKER = os.environ.get("IN_DOCKER")


async def send_log_to_remote_storage(logs):
    try:
        host = "localhost"
        if IN_DOCKER:
            host = "timescale_db"
        conn = await asyncpg.connect(
            host=host,
            port=5432,
            user="myuser",
            password="hey_NSA",
            database="mydb",
            timeout=6.0,
            command_timeout=8.0,
        )

        all_logs = []
        for i in logs:
            time = datetime.datetime.strptime(i["time"], "%Y-%m-%d %H:%M:%S.%f%z")
            application_name = i["application_name"]
            environment_name = i["environment_name"]
            log_event = i["log_event"]
            trace_id = i["trace_id"]
            file_path = i["file_path"]
            host_ip = i["host_ip"]
            data = i.get("data")
            if data:
                data = json.dumps(data)

            all_logs.append(
                (
                    time,
                    application_name,
                    environment_name,
                    log_event,
                    trace_id,
                    file_path,
                    host_ip,
                    data,
                )
            )

        # batch insert
        await conn.executemany(
            """
            INSERT INTO logs(time, application_name, environment_name, log_event, trace_id, file_path, host_ip, data) VALUES($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            all_logs,
            timeout=8.0,
        )

        await conn.close()
        logger.info("{}".format({"event": "log_sender_insert_end"}))
    except Exception as e:
        logger.exception("{}".format({"event": "send_log_to_remote_storage", "error": str(e)}))


async def schedule_log_sending():
    while True:
        async with batchedLogs.lock:
            batch_logs = batchedLogs.batch_logs
            if len(batch_logs) > 0:
                await send_log_to_remote_storage(logs=batch_logs)
                batchedLogs.batch_logs = []

        await asyncio.sleep(batchedLogs.send_logs_every())
