import sys, os
import tempfile
import subprocess
import logging
_logger = logging.getLogger(__name__)

import wordpress_cd.drivers as drivers
from wordpress_cd.build import get_artefact_dir


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
    _logger.info("Deploying '{0}' plugin using {1} driver...".format(driver.get_module_name(), driver))
    return driver.deploy_plugin()

def deploy_theme(args):
    driver = _driver(args)
    _logger.info("Deploying '{0}' theme using {1} driver...".format(driver.get_module_name(), driver))
    return driver.deploy_theme()

def deploy_site(args):
    driver = _driver(args)
    _logger.info("Deploying site using {0} driver...".format(driver))
    return driver.deploy_site()

def unpack_artefact():
    # Determine artefact filename and presence
    work_dir = os.getcwd()
    module_id = os.getenv("JOB_BASE_NAME", os.path.basename(os.getcwd()))
    zip_file = "{0}/{1}.zip".format(get_artefact_dir(work_dir), module_id)

    # Make temporary directory and move to it
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)

    # Unpack the artefact
    _logger.info("Unpacking module build artefact '{0}'...".format(module_id))

    # Sync new site into place, leaving config/content in place
    unpackargs = [
        "unzip", zip_file
    ]
    exitcode = subprocess.call(unpackargs)
    _logger.debug("unzip exitcode: {0}".format(exitcode))
    if exitcode != 0:
        logger.error("Unable to unpack build artefact. Exit code: {0}".format(exitcode))
        return exitcode

    return tmp_dir
