import logging
_logger = logging.getLogger(__name__)

from .job import JobHandler, get_artefact_dir
from .notifications import *

import wordpress_cd.drivers as drivers


class TestException(Exception):
    pass


class TestJobHandler(JobHandler):
    def _test_handling_exceptions(self):
        try:
            notify_start("test")
            self.test()
            notify_success("test")
            return 0
        except Exception as e:
            _logger.exception(str(e))
            self._handle_exception(e)
            notify_failure("test", str(e))
            return 1


class TestSiteJobHandler(TestJobHandler):
    def __init__(self, args):
        super(TestSiteJobHandler, self).__init__("site", None, args)

    # Defines a default workflow for a 'test' stage, which assumes we will
    # fire up a new site, run tests then tear the test site down...
    def test(self):
        driver = drivers.load_driver(self.args)
        _logger.info("Deploying transient copy of site using {0} driver...".format(driver))

        try:
            # Prepare the transient copy of site to be tested
            driver.test_site_setup()

            # Run the tests
            driver.test_site_run()

        finally:
            # Garbage collect the transient site copy
            driver.test_site_teardown()


def test_site(args):
    job = TestSiteJobHandler(args)
    return job._test_handling_exceptions()


# TODO: Test stages are still to be implemented.
#
# Ideally, a test site will be used and Amazon Device Farm will be pointed to
# that site and test suites triggered. Something like that.
#

def _test_module(args, type):
    raise NotImplementedError()

def test_plugin(args):
    _test_module(args, "plugin")

def test_theme(args):
    _test_module(args, "theme")
