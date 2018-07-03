import logging
_logger = logging.getLogger(__name__)

import wordpress_cd.drivers as drivers
from wordpress_cd.build import get_artefact_dir

# Defines a default workflow for a 'test' stage, which assumes we will
# fire up a new site, run tests then tear the test site down...
def test_site(args):
    driver = drivers.load_driver(args)
    _logger.info("Deploying transient copy of site using {0} driver...".format(driver))

    try:
        # Prepare the transient copy of site to be tested
        driver.test_site_setup()

        # Run the tests
        driver.test_site_run()

    finally:
        # Garbage collect the transient site copy
        driver.test_site_teardown()


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
