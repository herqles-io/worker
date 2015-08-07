from abc import ABCMeta, abstractmethod
import subprocess
import tempfile
import traceback
import logging
import os

class ActionProcessor(object):
    __metaclass__ = ABCMeta

    def __init__(self, worker, name, args):
        self.logger = logging.getLogger("hq.worker.processor")
        self.worker = worker
        self.name = name
        self.args = {}
        for arg in args:
            self.args[arg] = None

    def populateArgs(self, givenargs):
        for argkey in self.args.keys():
            if argkey in givenargs:
                self.args[argkey] = givenargs[argkey]

    @abstractmethod
    def work(self):
        return 0, ""

    def do_work(self, arguments):
        self.populateArgs(arguments)
        try:
            (exitcode, error) = self.work()
        except Exception:
            (exitcode, error) = -1, traceback.format_exc()

        return exitcode, error

    def read_env_file(self, file):
        env = {}

        if not os.path.isfile(file):
            return None

        with open(file, "r") as f:
            for line in f:
                line = line.strip()
                if '=' not in line:
                    continue
                key, value = line.split("=", 1)
                env[key] = value

        return env

    def run_command(self, command, cwd=None, env=None):
        stderr = tempfile.TemporaryFile()
        if env is None:
            env = os.environ.copy()
        process = subprocess.Popen(command, stderr=stderr, cwd=cwd, env=env)
        process.wait()
        stderr.seek(0)
        error = stderr.read().strip()
        stderr.close()
        return process.returncode, error
