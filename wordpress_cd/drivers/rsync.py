# Driver superclass to implement rsync-based deployment functions

import os
import subprocess
import logging
_logging = logging.getLogger(__name__)

from wordpress_cd.drivers import driver
from wordpress_cd.drivers.base import BaseDriver


@driver('rsync')
class RsyncDriver(BaseDriver):
    def __str__(self):
        return "rsync"

    def __init__(self, args):
        _logging.debug("Initialising rsync driver")
        super(RsyncDriver, self).__init__(args)

        self.ssh_host = os.getenv('SSH_HOST')
        self.ssh_port = os.getenv('SSH_PORT')
        self.ssh_user = os.getenv('SSH_USER')
        self.ssh_pass = os.getenv('SSH_PASS')
        self.ssh_path = os.getenv('SSH_PATH')

    def _get_rsync_rsh(self):
        rsync_rsh = "ssh -v -o StrictHostKeyChecking=no"

        # Is a specific port set?
        if self.ssh_port is not None:
            rsync_rsh += " -p {0}".format(self.ssh_port)

        # Should we feed the password in?
        if self.ssh_pass is not None:
            rsync_rsh = "sshpass -p {0} {1}".format(self.ssh_pass, rsync_rsh)

        return rsync_rsh

    def _deploy_module(self, type, module_id):
        _logging.info("Deploying of '{0}' {1} branch '{2}' to host '{3}' (job id: {4})...".format(module_id, type, self.git_branch, self.ssh_host, self.job_id))

        # Sync new site into place, leaving config/content in place
        pluginroot = "{0}/wp-content/{1}s/{2}".format(self.ssh_path, type, module_id)
        deployargs = [
            "rsync", "-r",
            "-e", self._get_rsync_rsh(),
            "--exclude=.git*",
            "--delete",
            ".", "{0}@{1}:{2}".format(self.ssh_user, self.ssh_host, pluginroot)
        ]
        deployenv = os.environ.copy()
        deployproc = subprocess.Popen(deployargs, stderr=subprocess.PIPE, env=deployenv)
        deployproc.wait()
        exitcode = deployproc.returncode
        _logging.debug("rsync exitcode: {0}".format(exitcode))
        if exitcode != 0:
            logging.error("Unable to sync new copy of plugin into place. Exit code: {0}".format(exitcode))
            return exitcode

        # Done
        _logging.info("Deployment of '{0}' {1} branch '{2}' to host '{3}' successful (job id: {4})...".format(module_id, type, self.git_branch, self.ssh_host, self.job_id))
        return 0

    def deploy_site(self):
        _logging.info("Deploying branch '{0}' to site '{1}' (job id: {2})...".format(self.git_branch, self.ssh_host, self.job_id))

        # Sync new site into place, leaving config/content in place
        work_dir = os.getcwd()
        os.chdir("build/wordpress")
        deployargs = [
            "rsync", "-r",
            "-e", self._get_rsync_rsh(),
            "--exclude=wp-config.php",
            "--exclude=wp-salt.php",
            "--exclude=wp-content/uploads",
            "--delete",
            "--protocol=28",
            ".", "{0}@{1}:{2}".format(self.ssh_user, self.ssh_host, self.ssh_path)
        ]
        deployenv = os.environ.copy()
        deployproc = subprocess.Popen(deployargs, stderr=subprocess.PIPE, env=deployenv)
        deployproc.wait()
        exitcode = deployproc.returncode
        _logging.debug("rsync exitcode: {0}".format(exitcode))
        if exitcode != 0:
            logging.error("Unable to sync new site into place. Exit code: {0}".format(exitcode))
            logging.debug(deployproc.stderr.read())
            return exitcode

        # Done
        _logging.info("Deployment of branch '{0}' to site '{1}' successful (job id: {2})...".format(self.git_branch, self.ssh_host, self.job_id))
        os.chdir(work_dir)
        return 0
