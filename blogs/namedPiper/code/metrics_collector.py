import os
import time

from metrics_sender import send_metrics_to_remote_storage


import logging
import asyncio

logger = logging.getLogger("metrics.collector")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s\n\n")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel("DEBUG")

logger.info("{}".format({"event": "metrics_collector_start"}))

# NB: collector should not try to create named pipe
# instead it should use the named pipe that was attached
# to it by the metrics_emitter container
fifo_file = "/tmp/namedPipes/komusNamedPipe"


async def collect_metrics():
    try:
        pipe = os.open(
            fifo_file, os.O_RDONLY | os.O_NONBLOCK | os.O_ASYNC
        )  # os.O_NONBLOCK is not available in Windows
        logger.info("{}".format({"event": "metrics_collector_read"}))
        while True:
            # TODO figure out how to read exactly oneline
            read_at_most = 4096  # with 4096 we are trying to read more than is sent

            # TODO: we should readline
            data = os.read(pipe, read_at_most)
            if len(data) == 0:
                # End of the file
                await asyncio.sleep(1)
                continue
            logger.info("{}".format({"event": "metrics_collector_print_data", "data": data}))
            await send_metrics_to_remote_storage(data=data)
        os.close(pipe)
    except OSError as e:
        logger.debug("{}".format({"event": "metrics_collector_error", "error": str(e)}))
        if e.errno == 6:
            pass
        else:
            raise e

# TODO: use uvloop if extra perfomance is required
loop = asyncio.get_event_loop()
loop.run_until_complete(collect_metrics())
loop.close()
logger.info("{}".format({"event": "metrics_collector_end"}))
