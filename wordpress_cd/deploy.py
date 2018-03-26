import os

import logging
_logger = logging.getLogger(__name__)

import wordpress_cd.drivers as drivers


def _driver(args):
    # Load specified modules (or sane/current defaults)
    try:
        drivers_to_load = os.environ["WPCD_DRIVERS"]
    except KeyError:
        drivers_to_load = "wordpress_cd.drivers.rsync"
    for modulename in drivers_to_load.split(","):
        _logger.debug("Importing module '%s'" % modulename)
        try:
            module = __import__(modulename)
        except ImportError as e:
            _logger.error("Error importing module: %s" % e.__str__())

    # Find the driver registered for this platform
    try:
        platform = os.environ['WPCD_PLATFORM']
    except KeyError:
        platform = "rsync"
    try:
        driver = drivers.drivers[platform]
    except KeyError as e:
        _logger.error("Missing driver for platform '{0}'.".format(platform))
        raise Exception("Configuration error.")

    return driver(args)


def deploy_plugin(args):
    driver = _driver(args)
    _logger.info("Deploying plugin using {0} driver...".format(driver))
    return driver.deploy_plugin()

def deploy_theme(args):
    driver = _driver(args)
    _logger.info("Deploying theme using {0} driver...".format(driver))
    return driver.deploy_theme()

def deploy_site(args):
    driver = _driver(args)
    _logger.info("Deploying site using {0} driver...".format(driver))
    return driver.deploy_site()
