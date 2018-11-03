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


def log_structure(log_event, data):
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "time": str(now),
        "application_name": "WebApp",
        "environment_name": "production",
        "log_event": log_event,
        "trace_id": str(uuid.uuid4()),
        "file_path": os.path.realpath(__file__),
        "host_ip": host_ip_address,
        "data": data,
    }


async def emmit_logs():
    while True:
        try:
            pipe = os.open(fifo_file, os.O_WRONLY | os.O_NONBLOCK | os.O_ASYNC)
            log = log_structure(
                log_event="login",
                data={"user": "Shawn Corey Carter", "age": 48, "email": "someemail@email.com"},
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
        await asyncio.sleep(1)


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.run_until_complete(emmit_logs())
loop.close()
logger.info("{}".format({"event": "log_emitter_end"}))
