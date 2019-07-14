from backie.task import Task

# pip install redis requests
import requests


class EmailTask(Task):
    """
    task to send email to customer after they have ordered.
    """

    task_name = "EmailTask"

    def run(self, order_id, email_address):
        url = "https://httpbin.org/{0}/{1}".format(order_id, email_address)
        print(url)
        response = requests.get(url, timeout=5.0)
        print("response:: ", response)


if __name__ == "__main__":
    email_task = EmailTask()
    order_id = "24dkq40"
    address = "example@example.org"
    email_task.delay(order_id, address)
