from backie.task import BaseTask

# pip install redis requests
import requests


class EmailTask(BaseTask):
    """
    task to send email to customer after they have ordered.
    """

    task_name = "EmailTask"

    def run(self, order_id, email_address):
        # lets pretend httpbin.org is an email service provider
        url = "https://httpbin.org/{0}/{1}".format(order_id, email_address)
        print(url)
        response = requests.get(url, timeout=5.0)
        print("response:: ", response)


if __name__ == "__main__":
    order_id = "24dkq40"
    email_address = "example@example.org"
    email_task = EmailTask()
    email_task.delay(order_id, email_address)
