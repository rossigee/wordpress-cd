import os
import requests

import logging
_logger = logging.getLogger(__name__)

from . import notification_driver
from .base import BaseDriver

DISCORD_GREEN = 0x00ff00
DISCORD_RED = 0xff0000
DISCORD_GREY = 0x808080


# Notification driver for Discord notifications
@notification_driver('discord')
class DiscordDriver(BaseDriver):
    def __init__(self, args):
        BaseDriver.__init__(self, args)
        self.url = os.environ['WPCD_DISCORD_URL']

    def _notify(self, content, colour):
        data = {
            'embeds': [{
                'title': 'Notification',
                'color': colour,
                'description': content
            }]
        }
        try:
            r = requests.post(self.url, json=data)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            # print(r.text)
            logging.error("Unable to send Discord notification", err)

    def notify_stage_start(self, stage_ref):
        content = "(*{0}*) Stage started".format(stage_ref)
        self._notify(content, DISCORD_GREY)
        logging.info("Sent stage start notification for '{0}' via Discord.".format(stage_ref))

    def notify_stage_success(self, stage_ref, stats = None):
        content = "(*{0}*) Stage completed successfully".format(stage_ref)
        self._notify(content, DISCORD_GREEN)
        logging.info("Sent stage success notification for '{0}' via Discord.".format(stage_ref))

    def notify_stage_failure(self, stage_ref, message, stats = None, exc = None):
        content = "(*{0}*) FAILED: {1}".format(stage_ref, message)
        self._notify(content, DISCORD_RED)
        logging.info("Sent stage failure notification for '{0}' via Discord.".format(stage_ref))
