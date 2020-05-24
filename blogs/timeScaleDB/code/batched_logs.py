import random
import asyncio

from log_collector_loop import loop


class Buffer:
    def __init__(self, loop, interval=12):
        self.loop = loop
        self.interval = interval

        self.lock = asyncio.Semaphore(value=1, loop=self.loop)  # asyncio.Lock()
        self.buf = []

    def send_logs_every(self):
        jitter = random.randint(1, 9) * 0.1
        return self.interval + jitter


bufferedLogs = Buffer(loop=loop)
