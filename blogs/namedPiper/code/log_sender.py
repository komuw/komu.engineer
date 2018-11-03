import os
import json
import asyncpg
import datetime

from logger import getLogger

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

        # TODO: implement batch inserts
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

            await conn.execute(
                """
                INSERT INTO logs(time, application_name, environment_name, log_event, trace_id, file_path, host_ip, data) VALUES($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                time,
                application_name,
                environment_name,
                log_event,
                trace_id,
                file_path,
                host_ip,
                data,
                timeout=8.0,
            )

        await conn.close()
    except Exception as e:
        logger.exception("{}".format({"event": "send_log_to_remote_storage", "error": str(e)}))
