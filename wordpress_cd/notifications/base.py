import os

import logging
_logger = logging.getLogger(__name__)


# Abstract superclass for notification drivers
class BaseDriver(object):
    def __init__(self, args):
        self.args = args

    def notify_stage_start(self, stage_ref):
        raise NotImplementedError()

    def notify_stage_success(self, stage_ref, stats = None):
        raise NotImplementedError()

    def notify_stage_failure(self, stage_ref, message, stats = None, exc = None):
        raise NotImplementedError()
