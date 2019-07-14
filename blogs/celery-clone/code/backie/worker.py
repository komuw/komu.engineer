import json


class Worker:
    def __init__(self, task) -> None:
        self.task = task

    def run_task(self, *task_args, **task_kwargs):
        self.task.run(*task_args, **task_kwargs)

    def start(self,):
        while True:
            try:
                _dequeued_item = self.task.broker.dequeue(queue_name=self.task.task_name)
                dequeued_item = json.loads(_dequeued_item)
                task_id = dequeued_item["task_id"]
                task_args = dequeued_item["args"]
                task_kwargs = dequeued_item["kwargs"]

                print("running task: {0}".format(task_id))
                self.run_task(*task_args, **task_kwargs)
                print("succesful run of task: {0}".format(task_id))
            except Exception:
                print("Unable to execute task.")
                continue
