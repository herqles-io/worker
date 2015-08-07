import threading
from hqworker.messaging import RunTaskSubscriber, TaskStatusPublisher, AliveSubscriber
import logging
from threading import Thread, Event
from abc import ABCMeta, abstractmethod
import socket
from hqlib.rabbitmq.routing import Publisher as RoutingPublisher
import yaml
from hqlib.sql.models import TaskStatus
from hqlib.rabbitmq.rpc import RPCPublisher
from schematics.exceptions import ModelValidationError, ModelConversionError
import json
from schematics.models import Model
from schematics.types import StringType

class AbstractWorker(object):
    __metaclass__ = ABCMeta

    def __init__(self, framework_name):
        self.id = None
        self.framework_name = framework_name
        self.logger = logging.getLogger("hq.worker")
        self.rabbitmq = None
        self.config = None
        self.config_path = None

    def register(self, rabbitmq, config_path):
        self.rabbitmq = rabbitmq
        self.config_path = config_path
        self.load_config(self.config_path)

        RunTaskSubscriber(self.rabbitmq, self).start()
        AliveSubscriber(self.rabbitmq, self).start()

        tries = 0

        while self.id is None:
            tries += 1
            if tries > 5:
                self.logger.error("Did not get a register reply from manager")
                return False

            publisher = RPCPublisher(self.rabbitmq, "worker", "register")
            corr_id = publisher.publish({'target': self.worker_name(), 'framework': self.framework_name,
                                         'datacenter': self.config.datacenter, 'tags': self.get_tags()})

            if corr_id is None:
                self.logger.warning("RPC Worker Register corr_id is None")
                continue

            data = publisher.get_data(corr_id)

            if data is None:
                self.logger.warning("RPC Worker Register data is None")
                continue

            self.id = data['id']

        self.on_register()

        return True

    def config_class(self):
        class ConfigClass(Model):
            datacenter = StringType(required=True)

        return ConfigClass

    def load_config(self, path, is_reload=False):

        if self.config_class() is None:
            return None

        config = self.config_class()()  # Create a empty config

        if path is not None:
            try:
                with open(self.config_path, "r") as f:
                    try:
                        config = self.config_class()(yaml.load(f), strict=False)
                    except ModelConversionError as e:
                        self.logger.error("Could not create config for worker "+self.framework_name + " "+json.dumps(e.message))
                        return config

                try:
                    config.validate()
                except ModelValidationError as e:
                    config = self.config_class()()  # Reset back to empty config
                    self.logger.error("Could not validate config for worker "+self.framework_name + " "+json.dumps(e.message))
            except IOError as e:
                self.logger.error("Could not load config for worker "+self.framework_name+". "+e.message)
        else:
            self.logger.warning("Config Path is not defined for worker "+self.framework_name)

        self.config = config

        if is_reload:
            publisher = RoutingPublisher(self.rabbitmq, "worker", "reload")
            publisher.publish({'target': self.worker_name(), 'framework': self.framework_name, 'tags': self.get_tags()})
            publisher.close()

    def worker_name(self):
        return socket.gethostname()

    def process_task(self, task):
        class TaskThread(threading.Thread):

            def __init__(self, worker):
                super(TaskThread, self).__init__()
                self.worker = worker

            def run(self):
                heartbeat = WorkerHeartbeatThread(self.worker.rabbitmq, str(task.id))
                heartbeat.start()

                for action in task.actions:

                    self.worker.logger.info("Action has started "+action.processor)
                    exit_code, message = self.worker.do_work(action)

                    if exit_code != 0:
                        heartbeat.stop()
                        self.worker.logger.info("Task has failed. Error "+str(task.id)+" "+message)
                        TaskStatusPublisher(self.worker.rabbitmq).status(task.id, TaskStatus.FAILED.value, message)
                        return
                    self.worker.logger.info("Action has completed "+action.processor)

                heartbeat.stop()
                self.worker.logger.info("Task has completed "+task.name)
                TaskStatusPublisher(self.worker.rabbitmq).status(task.id, TaskStatus.FINISHED.value)

        thread = TaskThread(self)
        thread.start()
        thread.join()  # Block on thread while we wait for task to finish

    @abstractmethod
    def get_tags(self):
        return {}

    @abstractmethod
    def do_work(self, action):
        return 0, ""

    @abstractmethod
    def on_register(self):
        pass


class WorkerHeartbeatThread(Thread):

    def __init__(self, rabbitmq, task_id):
        super(WorkerHeartbeatThread, self).__init__()
        self.event = Event()
        self.rabbitmq = rabbitmq
        self.task_id = task_id
        self.logger = logging.getLogger("hq.worker.heartbeat")

    def run(self):
        while not self.event.wait(5):
            TaskStatusPublisher(self.rabbitmq).status(self.task_id, TaskStatus.RUNNING.value)
            self.logger.info("Sending heartbeat for task "+self.task_id)

    def stop(self):
        self.event.set()
