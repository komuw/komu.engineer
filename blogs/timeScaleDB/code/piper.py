import os
import asyncio


class PIPE:
    def __init__(self, mode, fifo_file_name="/tmp/namedPipes/komusNamedPipe"):
        self.mode = mode
        # NB: collector should not try to create named pipe
        # instead it should use the named pipe that was attached
        # to it by the log_emitter container
        self.fifo_file_name = fifo_file_name
        self.fifo_file = None

    def __enter__(self):
        self.fifo_file = open(self.fifo_file_name, mode=self.mode)
        os.set_blocking(self.fifo_file.fileno(), False)

        return self.fifo_file

    def __exit__(self, type, value, traceback):
        if self.fifo_file:
            self.fifo_file.close()

    async def __aenter__(self):
        self.fifo_file = open(self.fifo_file_name, mode=self.mode)
        os.set_blocking(self.fifo_file.fileno(), False)

        return await asyncio.sleep(-1, result=self.fifo_file)

    async def __aexit__(self, exc_type, exc, tb):
        if self.fifo_file:
            await asyncio.sleep(-1, result=self.fifo_file.close())
