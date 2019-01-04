import os
import subprocess
import tempfile

import logging
_logger = logging.getLogger(__name__)


def get_artefact_dir(work_dir):
    # Determine where we're going to place the resulting ZIP file
    try:
        return "{0}/{1}".format(work_dir, os.environ['WPCD_ARTEFACT_DIR'])
    except KeyError:
        return "{0}/wpcd-artefacts".format(work_dir)

# Still used?
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
        _logger.error("Unable to unpack build artefact. Exit code: {0}".format(exitcode))
        return exitcode

    return tmp_dir


# @abstractclass
class JobHandler:
    def __init__(self, type, name, args, job_id = None):
        self.type = type
        self.name = name
        self.args = args
        self.exception_handlers = []

        self.job_id = os.getenv("CI_JOB_ID", job_id)

        _logger.info("Initialising job handler for {0} '{1}' [job id: {2}]".format(self.type, self.name, self.job_id))

    def add_exception_handler(self, handler):
        # TODO: check for 'handle_exception' method existence
        _logger.info("Adding exception handler '{0}'".format(str(handler)))
        self.exception_handlers.append(handler)

    def _handle_exception(self, e):
        for eh in self.exception_handlers:
            try:
                _logger.info("Handling exception with {0}".format(str(eh)))
                eh.handle_exception(e, self.type, self.name)
            except Exception as e2:
                _logger.error("Exception handling exception with {0}: {1}".format(str(eh), str(e2)))
