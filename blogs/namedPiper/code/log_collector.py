import os
import json
import uvloop
import asyncio


from logger import getLogger
from log_sender import send_log_to_remote_storage


logger = getLogger(name="logs.collector")


logger.info("{}".format({"event": "log_collector_start"}))

# NB: collector should not try to create named pipe
# instead it should use the named pipe that was attached
# to it by the log_emitter container
fifo_file = "/tmp/namedPipes/komusNamedPipe"


async def collect_logs():
    try:
        pipe = os.open(
            fifo_file, os.O_RDONLY | os.O_NONBLOCK | os.O_ASYNC
        )  # os.O_NONBLOCK is not available in Windows
        logger.info("{}".format({"event": "log_collector_read"}))
        while True:
            # TODO figure out how to read exactly oneline
            read_at_most = 4096  # with 4096 we are trying to read more than is sent

            # TODO: we should readline
            data = os.read(pipe, read_at_most)
            if len(data) == 0:
                # End of the file
                await asyncio.sleep(1)
                continue

            logger.info("{}".format({"event": "log_collector_print_data", "data": data}))
            data = data.decode()
            log_events = data.split("\n")
            logs = await handle_logs(log_events=log_events)

            await send_log_to_remote_storage(logs=logs)
        os.close(pipe)
    except OSError as e:
        logger.debug("{}".format({"event": "log_collector_error", "error": str(e)}))
        if e.errno == 6:
            pass
        else:
            raise e


async def handle_logs(log_events):
    logs = []
    for i in log_events:
        try:
            log_event = json.loads(i)
            logs.append(log_event)
        except json.decoder.JSONDecodeError as e:
            logger.debug("{}".format({"event": "handle_logs", "error": str(e)}))
            pass
    return logs


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.run_until_complete(collect_logs())
loop.close()
logger.info("{}".format({"event": "log_collector_end"}))
