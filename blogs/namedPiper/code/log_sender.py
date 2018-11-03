import aiohttp


from logger import getLogger

logger = getLogger(name="logs.sender")

logger.info("{}".format({"event": "log_sender_start"}))


async def send_log_to_remote_storage(data):
    try:
        timeout = aiohttp.ClientTimeout(total=5.0)  # 5.0 seconds
        async with aiohttp.ClientSession(
            headers={"accept": "application/json"}, timeout=timeout
        ) as session:
            url = "https://httpbin.org/post"
            async with session.post(url, data=data) as response:
                response_data = await response.json()
                logger.info(
                    "{}".format({"event": "log_sender_end", "response_data": response_data})
                )

    except Exception as e:
        logger.debug("{}".format({"event": "log_sender_send_data", "error": str(e)}))
