import os

import logging
_logger = logging.getLogger(__name__ + ".init")

# Registry for notification handlers as they are initialiased/registered
notification_drivers = {}


# Decorator for registering notification drivers
def notification_driver(id):
    def register(handler_class):
        _logger.debug("Registering notification '%s' as '%s'" % (handler_class, id))
        notification_drivers[id] = handler_class({})
        return handler_class

    return register


# Notify start of stage for each loaded notification driver`
def notify_start(stage_ref):
    for id in notification_drivers:
        driver = notification_drivers[id]
        _logger.debug("Sending start notification for '%s' via '%s'" % (stage_ref, id))
        driver.notify_stage_start(stage_ref)


# Notify success for each loaded notification driver`
def notify_success(stage_ref, statistics = None):
    for id in notification_drivers:
        driver = notification_drivers[id]
        _logger.debug("Sending success notification for '%s' via '%s'" % (stage_ref, id))
        driver.notify_stage_success(stage_ref, statistics)


# Notify failure for each loaded notification driver`
def notify_failure(stage_ref, message, statistics = None):
    for id in notification_drivers:
        driver = notification_drivers[id]
        _logger.debug("Sending failure notification for '%s' via '%s'" % (stage_ref, id))
        driver.notify_stage_failure(stage_ref, message, statistics)


# Load specified notification modules
try:
    notifications_to_load = os.environ["WPCD_NOTIFICATIONS"]
    for modulename in notifications_to_load.split(","):
        _logger.debug("Importing notification module '%s'" % modulename)
        try:
            module = __import__(modulename)
        except ImportError as e:
            _logger.exception("Error importing module '%s' for notification driver" % (modulename))

except KeyError:
    _logger.info("No notifications configured.")
