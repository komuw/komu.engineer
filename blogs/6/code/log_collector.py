import json
import asyncio


import piper
from logger import getLogger
from log_collector_loop import loop
from batched_logs import bufferedLogs
from log_sender import schedule_log_sending


logger = getLogger(name="logs.collector")
logger.info("{}".format({"event": "log_collector_start"}))


async def collect_logs():
    async with piper.PIPE(mode="r") as f:
        while True:
            try:
                logger.info("{}".format({"event": "log_collector_read"}))
                data = f.readline()
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
                    async with bufferedLogs.lock:
                        bufferedLogs.buf.append(log)
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
