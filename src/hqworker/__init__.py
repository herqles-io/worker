import json

import os
from yaml import YAMLError

from schematics.exceptions import ModelValidationError, ModelConversionError

from hqlib.rabbitmq import RabbitMQ
from hqworker.config import parse_config, BaseConfig, RabbitMQConfig, PathConfig
from hqlib.daemon import Daemon


class WorkerDaemon(Daemon):
    def __init__(self, args):
        super(WorkerDaemon, self).__init__("Worker")
        self.args = args
        self.path_config = None
        self.rabbitmq_config = None
        self.rabbitmq = None
        self.workers = []

    def setup(self):
        try:
            base_config = parse_config(self.args.config)
        except YAMLError as e:
            self.logger.error("Could not load worker config " + str(e))
            return False
        except IOError as e:
            self.logger.error("Could not load worker config " + e.message)
            return False

        try:
            base_config = BaseConfig(base_config, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create base config " + json.dumps(e.message))
            return False

        try:
            base_config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate base config " + json.dumps(e.message))
            return False

        try:
            self.path_config = PathConfig(base_config.paths, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create path config " + json.dumps(e.message))
            return False

        try:
            self.path_config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate path config " + json.dumps(e.message))
            return False

        try:
            self.rabbitmq_config = RabbitMQConfig(base_config.rabbitmq, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create rabbitmq config " + json.dumps(e.message))
            return False

        try:
            self.rabbitmq_config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate rabbitmq config " + json.dumps(e.message))
            return False

        return True

    def run(self):
        hosts = []
        for host in self.rabbitmq_config.hosts:
            (ip, port) = host.split(":")
            hosts.append((ip, int(port)))

        self.rabbitmq = RabbitMQ(hosts, self.rabbitmq_config.username, self.rabbitmq_config.password,
                            self.rabbitmq_config.virtual_host)
        self.rabbitmq.setup_database()

        for config_name in os.listdir(self.path_config.worker_configs):

            if not config_name.endswith(".yml") and not config_name.endswith(".yaml"):
                continue

            config_path = self.path_config.worker_configs + "/" + config_name
            try:
                worker_config = parse_config(config_path)
            except YAMLError as e:
                self.logger.error("Could load worker config " + config_name + " " + str(e))
                continue

            if 'module' not in worker_config:
                self.logger.error("Worker config " + config_name + " does not have a module to load.")
                continue

            modules = worker_config['module'].split(".")
            try:
                module = __import__(worker_config['module'])
                modules.pop(0)
                for m in modules:
                    module = getattr(module, m)
                worker = getattr(module, 'Worker')

                worker = worker()
                self.workers.append(worker)

            except:
                self.logger.exception("Error loading worker module " + worker_config['module'])
                continue

            if not worker.register(self.rabbitmq, config_path):
                self.logger.error("Worker " + worker.framework_name + " could not register")

        if len(self.workers) == 0:
            self.logger.warning("No workers loaded")
            return False

        return True

    def on_shutdown(self, signum=None, frame=None):
        for subscriber in list(self.rabbitmq.active_subscribers):
            subscriber.stop()

    def on_reload(self, signum=None, frame=None):
        self.logger.info("Reloading worker config files")

        for worker in self.workers:
            worker.load_config(worker.config_path, True)

    def get_pid_file(self):
        return self.path_config.pid

    def get_log_path(self):
        return self.path_config.logs


def main(args):
    daemon = WorkerDaemon(args)
    daemon.start()
