import sys, os
import tempfile
import subprocess

import logging
_logger = logging.getLogger(__name__)

from .job import JobHandler, get_artefact_dir
from .notifications import *

import wordpress_cd.drivers as drivers
from wordpress_cd.build import get_artefact_dir


class DeployException(Exception):
    pass


class DeployJobHandler(JobHandler):
    def _deploy_handling_exceptions(self):
        try:
            notify_start("deploy")
            self.deploy()
            notify_success("deploy")
            return 0
        except Exception as e:
            _logger.exception(str(e))
            self._handle_exception(e)
            notify_failure("deploy", str(e))
            return 1


class DeployModuleJobHandler(DeployJobHandler):
    def deploy(self):
        driver = drivers.load_driver(self.args)
        _logger.debug("Deploying '{0}' {1} using {2} driver".format(self.name, self.type, driver))

        # Invoke the driver's deploy method
        driver._deploy_module(self.type)


class DeploySiteJobHandler(DeployJobHandler):
    def __init__(self, args):
        super(DeploySiteJobHandler, self).__init__("site", None, args)

    def deploy(self):
        driver = drivers.load_driver(self.args)
        _logger.debug("Deploying site using {0} driver.".format(driver))

        # Invoke the driver's deploy method
        driver.deploy_site()


def deploy_site(args):
    job = DeploySiteJobHandler(args)
    return job._deploy_handling_exceptions()

def deploy_plugin(args):
    module_id = os.getenv("JOB_BASE_NAME", os.path.basename(os.getcwd()))
    job = DeployModuleJobHandler("plugin", module_id, args)
    return job._deploy_handling_exceptions()

def deploy_theme(args):
    module_id = os.getenv("JOB_BASE_NAME", os.path.basename(os.getcwd()))
    job = DeployModuleJobHandler("theme", module_id, args)
    return job._deploy_handling_exceptions()
