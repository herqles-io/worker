# Herqles Worker

The Worker executes tasks sent by the Manager.

# Version 2.0

This version is a compelte rewrite and is not compatible with older versions. 
Please use caution when upgrading.

## Requirements

* Herqles Manager
* RabbitMQ Server(s)
* Python 2.7
    * Not tested with newer python versions
 
## Quick Start Guide

Install HQ-Worker into a python environment

```
pip install hq-worker'
```

Install Worker implementations

```
pip install myworker
```

Setup the configuration for the Worker

```yaml
rabbitmq:
  hosts:
    - "10.0.0.1:5672"
    - "10.0.0.2:5672"
    - "10.0.0.3:5672"
  username: "root"
  password: "root"
  virtual_host: "herqles"
paths:
  logs: '/var/logs/herqles'
  pid: '/var/lock/herqles/worker.pid'
  worker_configs: '/etc/herqles/hq-worker/config.d'
```

Setup the configuration for any worker implementations in the worker_configs folder

worker_configs/myworker.yml
```yaml
module: 'my.awesome.worker'
```

Run the Worker

```
hq-worker -c config.yml
```

You now have a fully functional Worker for the Herqles system.
