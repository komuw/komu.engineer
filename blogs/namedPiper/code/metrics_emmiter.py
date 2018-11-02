import os
import errno
import logging

import json

from my_fifo import makeFifo


"""
run this as:
> python code/metrics_emmiter.py

TODO: use async operations; eg reading the pipe, writing to pipe etc
"""

fifo_file = makeFifo()


def emmit_metrics():
    try:
        pipe = os.open(fifo_file, os.O_WRONLY | os.O_NONBLOCK)
        for i in range(0, 5):
            msg = "DirectWriting-{}".format(i)
            write_data = json.dumps({"event": "myLogEvent", "myMessage": msg}) + "\n"
            write_data = write_data.encode()
            os.write(pipe, write_data)
        # os.fsync(pipe)  # Force write of file with filedescriptor, pipe to disk
        os.close(pipe)
    except OSError as e:
        print("exception occured. error={}".format(e))
        if e.errno == 6:
            # device not configured
            # raised when emmiter is called but collector aint there
            pass
        else:
            raise e


for i in range(0, 25):
    emmit_metrics()

print("end")
