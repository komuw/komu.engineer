import os
import errno

"""
use linux named pipes.

The linux pipe buffers are implemnted as circular buffers[1].
A consequence of the circular buffer is that when it is full and a subsequent write is performed:
  (a) then it starts overwriting the oldest data[2].
  (b) Alternatively, the routines that manage the buffer could prevent overwriting the data and return an error or raise an exception.
Whether or not data is overwritten is up to the semantics of the buffer routines or the application using the circular buffer[2].

The only difference between pipes and FIFOs is the manner in which they are created and opened. 
Once these tasks have been accomplished, I/O on pipes and FIFOs has exactly the same semantics[3].

Since Linux 2.6.11, the pipe capacity is 16 pages(65,536bytes ie 65KB).
The command:
  cat /proc/sys/fs/pipe-max-size
  1048576 == 1MB
shows the value that acts as a ceiling on the default capacity of a new pipe[3]

TODO: 
A. load test.
B. unit tests
C. use async operations on the python3 side(the metrics emitter has to be python2 but collector can be python3)  
   I would expect python3 async to perform really well.

1. http://www.pixelbeat.org/programming/stdio_buffering/
2. https://en.wikipedia.org/wiki/Circular_buffer
3. http://man7.org/linux/man-pages/man7/pipe.7.html
"""


def makeFifo(fifo_directory="/tmp/namedPipes", fifo_file="komusNamedPipe"):
    fifo_file = os.path.join(fifo_directory, fifo_file)
    try:
        os.mkdir(fifo_directory, 0777)
    except OSError as e:
        if e.errno == 17:
            # File exists
            pass
        else:
            raise e

    try:
        os.mkfifo(fifo_file, 0777)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    return fifo_file
