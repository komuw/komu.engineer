import os
import asyncio

import json
import uvloop


from my_fifo import makeFifo
from logger import getLogger

logger = getLogger(name="metrics.emitter")
logger.info("{}".format({"event": "log_emitter_start"}))

fifo_file = makeFifo()


async def emmit_metrics():
    while True:
        try:
            pipe = os.open(fifo_file, os.O_WRONLY | os.O_NONBLOCK | os.O_ASYNC)
            for i in range(0, 5):
                msg = "DirectWriting-{}".format(i)
                write_data = json.dumps({"event": "myLogEvent", "myMessage": msg}) + "\n"
                write_data = write_data.encode()
                os.write(pipe, write_data)
            os.close(pipe)
        except OSError as e:
            logger.debug("{}".format({"event": "log_emitter_error", "error": str(e)}))
            if e.errno == 6:
                # device not configured
                # raised when emmiter is called but collector aint there
                pass
            else:
                raise e
        await asyncio.sleep(1)


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.run_until_complete(emmit_metrics())
loop.close()
logger.info("{}".format({"event": "log_emitter_end"}))
