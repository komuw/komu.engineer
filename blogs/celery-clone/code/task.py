import abc
import json
import uuid

from broker import Broker


class Task(abc.ABC):
    task_name = None

    def __init__(self):
        if not self.task_name:
            raise ValueError("task_name should be set")
        self.broker = Broker()

    @abc.abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError("Task `run` method must be implemented.")

    def delay(self, *args, **kwargs):
        try:
            task_id = str(uuid.uuid4())
            _task = {"task_id": task_id, "args": args, "kwargs": kwargs}
            serialized_task = json.dumps(_task)
            self.broker.enqueue(queue_name=self.task_name, item=serialized_task)
        except Exception:
            raise Exception("Unable to publish task to the broker.")
