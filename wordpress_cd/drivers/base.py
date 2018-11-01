import os
import logging
_logger = logging.getLogger(__name__)

import random, string

def randomword(length):
   letters = string.ascii_lowercase
   return ''.join(random.choice(letters) for i in range(length))


# Abstract superclass for deployment drivers
class BaseDriver(object):
    def __init__(self, args, test_dataset = None):
        self.args = args
        self.test_dataset = test_dataset

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

        # Does this site use non-standard dirs for uploads and plugins?
        self.wp_content_dir = os.getenv("WP_CONTENT_DIR", "/wp-content")
        self.wp_plugin_dir = os.getenv("WP_PLUGIN_DIR", "/wp-content/plugins")

        # For test stage, select a random uid to use in hostname
        self.test_site_uid = randomword(10)
        self.test_site_domain = os.getenv("WPCD_TEST_DOMAIN", "test.yourdomain.com")
        self.test_site_fqdn = "wpcd-{}.{}".format(self.test_site_uid, self.test_site_domain)
        self.test_site_url = "https://" + self.test_site_fqdn

        # Flags for setup and teardown of test sites
        self.is_site_set_up = False
        self.is_dns_set_up = False
        self.is_ssl_set_up = False

    def get_module_name(self):
        return os.path.basename(os.getcwd())

    def deploy_theme(self):
        self._deploy_module("theme")

    def deploy_plugin(self):
        self._deploy_module("plugin")

    def deploy_mu_plugin(self):
        self._deploy_module("mu_plugin")

    def _deploy_module(self, type):
        raise NotImplementedError()

    def deploy_site(self):
        raise NotImplementedError()

    def deploy_host(self):
        _logger.warn("Use of 'deploy_host' deprecated. Use 'deploy_site' instead.")
        self.deploy_site()

    def test_site(self):
        raise NotImplementedError()

    def test_site_setup(self):
        _logger.info("Firing up transient test environment with hostname '{}'".format(self.test_site_fqdn))

        # Set up virtualhost, deploy document root and initialise db etc
        self._setup_host()
        self.is_site_set_up = True

        # Set up DNS entry
        self._setup_dns()
        self.is_dns_set_up = True

        # Configure site to use wildcard certificate
        self._setup_ssl()
        self.is_ssl_set_up = True

        # Notification/webhook with details of the test host that has been set up?

        # Schedule site teardown to occur later asynchronously?

    def test_site_run(self):
        _logger.info("Running test suites against URL: {}".format(self.test_site_url))

        # TODO: Ensure that at least the homepage is returning an expected response...

        # Intended to be a placefolder for real tests to be run against the host.

    def test_site_teardown(self):
        _logger.info("Tearing down transient test environment with hostname '{}'".format(self.test_site_fqdn))

        # Remove Beanstalk virtualhost and database
        if self.is_site_set_up:
            self._teardown_host()

        # Remove DNS entry
        if self.is_dns_set_up:
            self._teardown_dns()

        # Revoke SSL certificate (if necessary)
        if self.is_ssl_set_up:
            self._teardown_ssl()

        # Notification/webhook with details of the test host that has now been released?

    def _setup_db(self):
        _logger.info("Creating database and user ('{}')...".format(self.test_dataset.mysql_db))
        cnx = self._get_db_connection()
        cursor = cnx.cursor()

        # Create a new database on the RDS server
        sql = "CREATE DATABASE `{}`".format(
            self.test_dataset.mysql_db
        )
        cursor.execute(sql)

        # Add user with privileges to access this database
        sql = "GRANT ALL ON `{}`.* TO `{}` IDENTIFIED BY \"{}\"".format(
            self.test_dataset.mysql_db,
            self.test_dataset.mysql_user,
            self.test_dataset.mysql_pass
        )
        cursor.execute(sql)

        # Wind down db commection
        cnx.commit()
        cursor.close()
        cnx.close()

    def _teardown_db(self):
        cnx = self._get_db_connection()
        cursor = cnx.cursor()

        # Drop DB
        sql = "DROP DATABASE IF EXISTS `{}`".format(
            self.test_dataset.mysql_user
        )
        cursor.execute(sql)

        # Delete user
        sql = "DROP USER IF EXISTS `{}`".format(
            self.test_dataset.mysql_user
        )
        cursor.execute(sql)

        # Wind down db commection
        cnx.commit()
        cursor.close()
        cnx.close()
