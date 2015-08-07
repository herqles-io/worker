from hqlib.rabbitmq.routing import Publisher as RoutingPublisher

class TaskStatusPublisher(RoutingPublisher):

    def __init__(self, rabbitmq):
        super(TaskStatusPublisher, self).__init__(rabbitmq, "task", "task_status")

    def status(self, task_id, status, message=""):
        self.publish({"task_id": task_id, "status": status, "message": message})
        self.close()
