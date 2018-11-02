import os
import time


"""
run this as:
in terminal 1:
> python metrics_collector.py

in terminal 2:
> echo "sina tabu" > komusNamedPipe



The linux pipe buffers are implemnted as circular buffers[1].
A consequence of the circular buffer is that when it is full and a subsequent write is performed:
  (a) then it starts overwriting the oldest data[2].
  (b) Alternatively, the routines that manage the buffer could prevent overwriting the data and return an error or raise an exception.
Whether or not data is overwritten is up to the semantics of the buffer routines or the application using the circular buffer[2].
TODO: investigate whether namedPipes in Linux overwrite data [as in (a) above or raise error as in (b)]
TODO: use async operations; eg reading the pipe, writing to pipe etc

1. http://www.pixelbeat.org/programming/stdio_buffering/
2. https://en.wikipedia.org/wiki/Circular_buffer
"""

import logging

logger = logging.getLogger("metrics.collector")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel("DEBUG")

logger.info("{}".format({"event": "metrics_collector_start"}))

# NB: collector should not try to create named pipe
# instead it should use the named pipe that was attached
# to it by the metrics_emitter container
fifo_file = "/tmp/namedPipes/komusNamedPipe"


def collect_metrics():
    try:
        pipe = os.open(
            fifo_file, os.O_RDONLY | os.O_NONBLOCK
        )  # os.O_NONBLOCK is not available in Windows
        logger.info("{}".format({"event": "metrics_collector_read"}))
        while True:
            # TODO figure out how to read exactly oneline
            read_at_most = 2048  # with 2048 we are trying to read more than is sent

            # TODO: we should readline
            data = os.read(pipe, read_at_most)
            if len(data) == 0:
                # End of the file
                time.sleep(3)
                continue
            logger.info("{}".format({"event": "metrics_collector_print_data", "data": data}))
        os.close(pipe)
    except OSError as e:
        logger.debug("{}".format({"event": "metrics_collector_error", "error": str(e)}))
        if e.errno == 6:
            pass
        else:
            raise e


collect_metrics()

logger.info("{}".format({"event": "metrics_collector_end"}))
