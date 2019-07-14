from ecommerce_tasks import EmailTask
from worker import Worker


if __name__ == "__main__":
    email_task = EmailTask()

    # run workers
    _worker = Worker(task=email_task)
    _worker.start()
