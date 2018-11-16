import os
import json
import uuid
import asyncio
import datetime


import uvloop


from my_fifo import makeFifo
from logger import getLogger
from get_ip import host_ip_address

logger = getLogger(name="logs.emitter")
logger.info("{}".format({"event": "log_emitter_start"}))

fifo_file = makeFifo()


def log_structure(log_event, trace_id, application_name, environment_name, file_path, data):
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "log_event": log_event,
        "trace_id": trace_id,
        "application_name": application_name,
        "environment_name": environment_name,
        "file_path": file_path,
        "data": data,
        "time": str(now),
        "host_ip": host_ip_address,
    }


async def emmit_logs(log_event, application_name, environment_name, file_path, log_event_data):
    try:
        pipe = os.open(fifo_file, os.O_WRONLY | os.O_NONBLOCK | os.O_ASYNC)
        log = log_structure(
            log_event=log_event,
            trace_id=str(uuid.uuid4()),
            application_name=application_name,
            environment_name=environment_name,
            file_path=file_path,
            data=log_event_data,
        )
        # we use newline to demarcate where one log event ends.
        write_data = json.dumps(log) + "\n"
        write_data = write_data.encode()
        os.write(pipe, write_data)
        os.close(pipe)
    except OSError as e:
        if e.errno == 6:
            # device not configured
            # raised when emmiter is called but collector aint there
            pass
        else:
            logger.exception("{}".format({"event": "log_emitter_error", "error": str(e)}))
            pass
    finally:
        # this sleep is important
        await asyncio.sleep(1)


async def web_app():
    await emmit_logs(
        log_event="login",
        application_name="WebApp",
        environment_name="production",
        file_path=os.path.realpath(__file__),
        log_event_data={"user": "Shawn Corey Carter", "age": 48, "email": "someemail@email.com"},
    )


async def worker():
    await emmit_logs(
        log_event="process_work",
        application_name="WorkerApp",
        environment_name="production",
        file_path=os.path.realpath(__file__),
        log_event_data={"worker_id": str(uuid.uuid4()), "datacenter": "us-west"},
    )


async def etl():
    await emmit_logs(
        log_event="video_process",
        application_name="ETL_app",
        environment_name="production",
        file_path=os.path.realpath(__file__),
        log_event_data={"etl_id": str(uuid.uuid4()), "jobType": "batch"},
    )


async def run():
    while True:
        await web_app()
        await worker()
        await etl()


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()


tasks = asyncio.gather(run(), run(), run(), run(), loop=loop)
loop.run_until_complete(tasks)


loop.close()
logger.info("{}".format({"event": "log_emitter_end"}))
