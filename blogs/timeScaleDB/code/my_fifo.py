import os
import errno


def makeFifo(fifo_directory="/tmp/namedPipes", fifo_file="komusNamedPipe"):
    fifo_file = os.path.join(fifo_directory, fifo_file)
    if os.path.exists(fifo_file):
        # make it indempotent to call it multiple times
        return fifo_file

    try:
        os.mkdir(fifo_directory, mode=0o777)
    except OSError as e:
        if e.errno == 17:
            # File exists
            pass
        else:
            raise e

    try:
        os.mkfifo(fifo_file, mode=0o777)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    return fifo_file
