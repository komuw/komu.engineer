import os
import json
import asyncio


from logger import getLogger
from batched_logs import batchedLogs
from log_sender import schedule_log_sending
from log_collector_loop import loop

logger = getLogger(name="logs.collector")


logger.info("{}".format({"event": "log_collector_start"}))

# NB: collector should not try to create named pipe
# instead it should use the named pipe that was attached
# to it by the log_emitter container
fifo_file = "/tmp/namedPipes/komusNamedPipe"


async def collect_logs():
    while True:
        try:
            pipe = os.open(
                fifo_file, os.O_RDONLY | os.O_NONBLOCK | os.O_ASYNC
            )  # os.O_NONBLOCK is not available in Windows
            logger.info("{}".format({"event": "log_collector_read"}))

            # TODO figure out how to read exactly oneline
            read_at_most = 4096  # with 4096 we are trying to read more than is sent

            # TODO: we should readline
            # TODO: try and port/add a readline implementation
            data = os.read(pipe, read_at_most)
            if len(data) == 0:
                # End of the file
                await asyncio.sleep(1)
                continue

            logger.info("{}".format({"event": "log_collector_print_data", "data": data}))
            data = data.decode()
            log_events = data.split("\n")
            logs = await handle_logs(log_events=log_events)

            # TODO: disable locks/batched log sending if we get
            # 'got Future attached to a different loop' errors
            async with batchedLogs.lock:
                batchedLogs.batch_logs = batchedLogs.batch_logs + logs
            os.close(pipe)
        except OSError as e:
            if e.errno == 6:
                pass
            else:
                logger.exception("{}".format({"event": "log_collector_error", "error": str(e)}))
                pass


async def handle_logs(log_events):
    # note: we will loose some logs since not all
    # are valid json because collect_logs() does a read of at most 4096 bytes
    # instead of reading one line
    logs = []
    for i in log_events:
        try:
            log_event = json.loads(i)
            logs.append(log_event)
        except json.decoder.JSONDecodeError:
            pass
    return logs


tasks = asyncio.gather(collect_logs(), schedule_log_sending(), loop=loop)
loop.run_until_complete(tasks)

loop.close()
logger.info("{}".format({"event": "log_collector_end"}))
