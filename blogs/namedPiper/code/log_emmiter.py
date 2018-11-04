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


def log_structure(
    log_event, application_name, file_path, data, environment_name="production", trace_id=None
):
    if not trace_id:
        trace_id = str(uuid.uuid4())

    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "time": str(now),
        "application_name": application_name,
        "environment_name": environment_name,
        "log_event": log_event,
        "trace_id": trace_id,
        "file_path": file_path,
        "host_ip": host_ip_address,
        "data": data,
    }


async def emmit_logs(log_event, application_name, file_path, log_event_data, trace_id=None):
    try:
        pipe = os.open(fifo_file, os.O_WRONLY | os.O_NONBLOCK | os.O_ASYNC)
        log = log_structure(
            log_event=log_event,
            application_name=application_name,
            file_path=file_path,
            data=log_event_data,
            trace_id=trace_id,
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
    import sys
    import traceback

    await emmit_logs(
        log_event="login",
        application_name="WebApp",
        file_path=os.path.realpath(__file__),
        log_event_data={"user": "Shawn Corey Carter", "age": 48, "email": "someemail@email.com"},
    )
    try:
        my_list = []
        my_list[4]
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        our_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
        await emmit_logs(
            log_event="login_error",
            application_name="WebApp",
            file_path=os.path.realpath(__file__),
            log_event_data={"error": "login_failed", "traceback": our_traceback},
        )


async def worker():
    await emmit_logs(
        log_event="process_work",
        application_name="WorkerApp",
        file_path=os.path.realpath(__file__),
        log_event_data={"worker_id": str(uuid.uuid4()), "datacenter": "us-west"},
    )


async def etl():
    async def step1(trace_id):
        await emmit_logs(
            log_event="video_process_step1",
            application_name="ETL_app",
            file_path=os.path.realpath(__file__),
            log_event_data={"etl_id": str(uuid.uuid4()), "jobType": "batch"},
            trace_id=trace_id,
        )

    async def step2(trace_id):
        await emmit_logs(
            log_event="video_process_step2",
            application_name="ETL_app",
            file_path=os.path.realpath(__file__),
            log_event_data={"etl_id": str(uuid.uuid4()), "jobType": "batch"},
            trace_id=trace_id,
        )

    async def step3(trace_id):
        await emmit_logs(
            log_event="video_process_step3",
            application_name="ETL_app",
            file_path=os.path.realpath(__file__),
            log_event_data={"etl_id": str(uuid.uuid4()), "jobType": "batch"},
            trace_id=trace_id,
        )

    trace_id = str(uuid.uuid4())
    await step1(trace_id)
    await step2(trace_id)
    await step3(trace_id)


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
