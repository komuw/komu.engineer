import abc
import json
import uuid

from . import broker


class Task(abc.ABC):
    task_name = None

    def __init__(self):
        self.broker = broker.Broker()
        self.task_name = self.task_name

    @abc.abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError("Task `run` method must be implemented.")

    def delay(self, *args, **kwargs):
        """
        Parameters:
            args: The positional arguments to pass on to the task.
            kwargs: The keyword arguments to pass on to the task.
        """
        task_id = str(uuid.uuid4())
        _task = {"task_id": task_id, "args": args, "kwargs": kwargs}
        serialized_task = json.dumps(_task)
        self.broker.enqueue(queue_name=self.task_name, item=serialized_task)
