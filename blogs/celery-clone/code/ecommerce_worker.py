from ecommerce_tasks import EmailTask

from backie.worker import Worker

if __name__ == "__main__":
    email_task = EmailTask()

    # run workers
    worker = Worker(task=email_task)
    worker.start()
