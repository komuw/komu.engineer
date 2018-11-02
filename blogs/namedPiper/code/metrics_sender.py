import asyncio, json, aiohttp

import logging

logger = logging.getLogger("metrics.sender")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s\n\n")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel("DEBUG")

logger.info("{}".format({"event": "metrics_sender_start"}))


async def send_metrics_to_remote_storage(data):
    try:
        timeout = aiohttp.ClientTimeout(total=5.0) # 5.0 seconds
        async with aiohttp.ClientSession(
            headers={"accept": "application/json"}, timeout=timeout
        ) as session:
            url = "https://httpbin.org/post"
            async with session.post(url, data=data) as response:
                response_data = await response.json()
                logger.info(
                    "{}".format({"event": "metrics_sender_end", "response_data": response_data})
                )

    except Exception as e:
        logger.debug("{}".format({"event": "metrics_sender_send_data", "error": str(e)}))
