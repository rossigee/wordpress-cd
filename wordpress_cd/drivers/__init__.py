import os

import logging
_logger = logging.getLogger(__name__ + ".init")

# Manage list of available deployment target platforms as they are initialised
drivers = {}


def driver(id):
    def register(handler_class):
        _logger.debug("Registering driver '%s' as '%s'" % (handler_class, id))
        drivers[id] = handler_class
        return handler_class

    return register
