import asyncio
from log_collector_loop import loop


class Batcher:
    def __init__(self):
        self.lock = asyncio.Semaphore(value=1, loop=loop)  # asyncio.Lock()
        self.batch_logs = []
        self.send_logs_every = 8.0  # seconds


batchedLogs = Batcher()
