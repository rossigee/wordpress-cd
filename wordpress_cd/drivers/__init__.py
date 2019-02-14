import os

import logging
_logger = logging.getLogger(__name__ + ".init")

# Manage list of available deployment target platforms as they are initialised
drivers = {}


def load_driver(args):
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
            _logger.exception("Error importing module '%s' for main driver" % (modulename))

    # Find the driver registered for this platform
    try:
        platform = os.environ['WPCD_PLATFORM']
    except KeyError:
        platform = "rsync"
    try:
        driver = drivers[platform]
    except KeyError as e:
        _logger.error("Missing driver for platform '{0}'.".format(platform))
        raise Exception("Configuration error.")

    return driver(args)


def driver(id):
    def register(handler_class):
        _logger.debug("Registering driver '%s' as '%s'" % (handler_class, id))
        drivers[id] = handler_class
        return handler_class

    return register
