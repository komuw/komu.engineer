import os
import errno

"""
use linux named pipes.

The linux pipe buffers are implemnted as circular buffers[1].
A consequence of the circular buffer is that when it is full and a subsequent write is performed:
  (a) then it starts overwriting the oldest data[2].
  (b) Alternatively, the routines that manage the buffer could prevent overwriting the data and return an error or raise an exception.
Whether or not data is overwritten is up to the semantics of the buffer routines or the application using the circular buffer[2].

1. http://www.pixelbeat.org/programming/stdio_buffering/
2. https://en.wikipedia.org/wiki/Circular_buffer
"""


def makeFifo(fifo_directory="/tmp/namedPipes", fifo_file="komusNamedPipe"):
    fifo_file = os.path.join(fifo_directory, fifo_file)
    try:
        os.mkdir(fifo_directory, mode=0o777)
    except FileExistsError:
        pass

    try:
        os.mkfifo(fifo_file, mode=0o777)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    return fifo_file
