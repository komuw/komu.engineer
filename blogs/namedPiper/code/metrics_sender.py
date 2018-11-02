import urllib.request, json

import logging

logger = logging.getLogger("metrics.sender")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s\n\n")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel("DEBUG")

logger.info("{}".format({"event": "metrics_sender_start"}))


# TODO: we should use an async http client in here
# eg: https://aiohttp.readthedocs.io/en/stable/
def send_metrics_to_remote_storage(data):
    try:
        url = "https://httpbin.org/post"
        req = urllib.request.Request(url=url, data=data, method="POST")
        req.add_header("accept", "application/json")

        response = urllib.request.urlopen(req, timeout=1.1)
        response_data = response.read()
        response_data = json.loads(response_data.decode())
        logger.info("{}".format({"event": "metrics_sender_end", "response_data": response_data}))

    except Exception as e:
        logger.exception("{}".format({"event": "metrics_sender_send_data", "error": str(e)}))
