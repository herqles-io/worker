from hqlib.rabbitmq.routing import Subscriber as RoutingSubscriber
from hqlib.rabbitmq.rpc import RPCReplyPublisher
import json
import logging
from hqworker.messaging.task import TaskStatusPublisher
from hqlib.sql.models import Task, TaskStatus, Action


class RunTaskSubscriber(RoutingSubscriber):

    def __init__(self, rabbitmq, worker):
        super(RunTaskSubscriber, self).__init__(rabbitmq, exchange_name="worker-"+worker.worker_name(),
                                                routing_key="run-"+worker.framework_name,
                                                queue_name="run-"+worker.framework_name+"@"+worker.worker_name(),
                                                auto_delete=False)
        self.logger = logging.getLogger("hq.worker.subscriber.runtask")
        self.worker = worker

    def message_deliver(self, channel, basic_deliver, properties, body):
        data = json.loads(body)

        task = Task(id=data['id'], name=data['name'])

        for action in data['actions']:
            action_obj = Action(processor=action['processor'], arguments=action['arguments'])
            task.actions.append(action_obj)

        self.logger.info("Received Run Task "+task.name)

        TaskStatusPublisher(self.rabbitmq).status(task.id, TaskStatus.RUNNING.value)

        self.worker.process_task(task)

        channel.basic_ack(basic_deliver.delivery_tag)


class AliveSubscriber(RoutingSubscriber):

    def __init__(self, rabbitmq, worker):
        super(AliveSubscriber, self).__init__(rabbitmq, "worker-"+worker.worker_name(), "alive-"+worker.framework_name)

    def message_deliver(self, channel, basic_deliver, properties, body):

        publisher = RPCReplyPublisher(self.rabbitmq, properties.reply_to, properties.correlation_id)
        publisher.publish({})
        publisher.close()

        channel.basic_ack(basic_deliver.delivery_tag)
