import os
import time
import errno
import logging

import json

from my_fifo import makeFifo


logger = logging.getLogger("metrics.emitter")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel("DEBUG")
logger.info("{}".format({"event": "metrics_emitter_start"}))


fifo_file = makeFifo()


def emmit_metrics():
    try:
        pipe = os.open(fifo_file, os.O_WRONLY | os.O_NONBLOCK | os.O_ASYNC)
        for i in range(0, 5):
            msg = "DirectWriting-{}".format(i)
            write_data = json.dumps({"event": "myLogEvent", "myMessage": msg}) + "\n"
            write_data = write_data.encode()
            os.write(pipe, write_data)
        os.close(pipe)
    except OSError as e:
        logger.debug("{}".format({"event": "metrics_emitter_error", "error": str(e)}))
        if e.errno == 6:
            # device not configured
            # raised when emmiter is called but collector aint there
            pass
        else:
            raise e


while True:
    emmit_metrics()
    time.sleep(1)


logger.info("{}".format({"event": "metrics_emitter_end"}))
