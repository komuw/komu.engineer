import os
import json
import asyncio


from logger import getLogger
from batched_logs import batchedLogs
from log_sender import schedule_log_sending
from log_collector_loop import loop

logger = getLogger(name="logs.collector")


logger.info("{}".format({"event": "log_collector_start"}))

# NB: collector should not try to create named pipe
# instead it should use the named pipe that was attached
# to it by the log_emitter container
fifo_file = "/tmp/namedPipes/komusNamedPipe"


class PIPE:
    fifo_file = None

    def __enter__(self):
        self.fifo_file = open(fifo_file, mode="r")
        os.set_blocking(self.fifo_file.fileno(), False)

        return self.fifo_file

    def __exit__(self, type, value, traceback):
        if self.fifo_file:
            self.fifo_file.close()

    async def __aenter__(self):
        self.fifo_file = open(fifo_file, mode="r")
        os.set_blocking(self.fifo_file.fileno(), False)

        return await asyncio.sleep(-1, result=self.fifo_file)

    async def __aexit__(self, exc_type, exc, tb):
        if self.fifo_file:
            await asyncio.sleep(-1, result=self.fifo_file.close())


async def collect_logs():
    async with PIPE() as pipe:
        while True:
            try:
                logger.info("{}".format({"event": "log_collector_read"}))
                data = pipe.readline()
                if len(data) == 0:
                    # End of the file
                    await asyncio.sleep(1)
                    continue

                logger.info("{}".format({"event": "log_collector_print_data", "data": data}))
                log = await handle_logs(log_event=data)

                # do not buffer if there are no logs
                if log:
                    # TODO: disable locks/batched log sending if we get
                    # 'got Future attached to a different loop' errors
                    async with batchedLogs.lock:
                        batchedLogs.batch_logs.append(log)
            except OSError as e:
                if e.errno == 6:
                    pass
                else:
                    logger.exception("{}".format({"event": "log_collector_error", "error": str(e)}))
                    pass


async def handle_logs(log_event):
    log = None
    try:
        log = json.loads(log_event)
    except json.decoder.JSONDecodeError:
        pass
    return log


tasks = asyncio.gather(collect_logs(), schedule_log_sending(), loop=loop)
loop.run_until_complete(tasks)

loop.close()
logger.info("{}".format({"event": "log_collector_end"}))
