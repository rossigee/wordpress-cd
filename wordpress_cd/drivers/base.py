import os
import logging
_logger = logging.getLogger(__name__)


# Abstract superclass for deployment drivers
class BaseDriver(object):
    def __init__(self, args):
        self.args = args

        # Which CI-specific envvars to use?
        if 'GITLAB_CI' in os.environ:
            _logger.debug("Detected GitLab CI")
            #self.git_repo = os.environ['CI_PROJECT_URL']
            self.git_branch = os.environ['CI_COMMIT_REF_NAME']
            self.target = os.environ['CI_JOB_NAME']
            self.job_id = os.environ['CI_JOB_ID']
        elif 'JENKINS_URL' in os.environ:
            _logger.debug("Detected Jenkins CI")
            #self.git_repo = os.environ['GIT_URL']
            self.git_branch = os.environ['GIT_BRANCH']
            self.target = os.environ['JOB_NAME']
            self.job_id = os.environ['BUILD_NUMBER']
        else:
            # Local development?
            _logger.debug("No specific CI system detected")
            #self.git_repo = os.environ['WPCD_GIT_URL']
            self.git_branch = os.environ['WPCD_GIT_BRANCH']
            self.target = os.environ['WPCD_JOB_NAME']
            self.job_id = os.environ['WPCD_JOB_ID']

    def deploy_theme(self, module_id):
        self._deploy_module("theme", module_id)

    def deploy_plugin(self, module_id):
        self._deploy_module("plugin", module_id)

    def deploy_mu_plugin(self, module_id):
        self._deploy_module("mu_plugin", module_id)

    def _deploy_module(self, type, module_id):
        raise NotImplementedError()

    def deploy_host(self):
        raise NotImplementedError()
