#
# Requires 'curl', 'tar' and 'unzip' O/S binaries installed and available.
#

import sys, os
import tempfile
import subprocess
import yaml
import logging
import shutil

import logging
_logger = logging.getLogger(__name__)

from .job import JobHandler, get_artefact_dir


def get_branch():
    if 'GITLAB_CI' in os.environ:
        _logger.debug("Detected GitLab CI")
        return os.environ['CI_COMMIT_REF_NAME']
    elif 'GIT_BRANCH' in os.environ:
        _logger.debug("Detected Jenkins CI")
        return os.environ['GIT_BRANCH']
    else:
        return "develop"

def is_develop_branch():
    return get_branch()[:7] == "develop"


class BuildException(Exception):
    pass


class BuildJobHandler(JobHandler):
    def _build_handling_exceptions(self):
        try:
            self.build()
            return 0
        except Exception as e:
            _logger.exception(str(e))
            self._handle_exception(e)
            return 1

    def check_and_run_gulpfile(self, src_dir):
        # If there is a 'package.json' present, run 'npm install'
        if os.path.isfile("{0}/package.json".format(src_dir)):
            _logger.info("Found 'package.json', running 'npm install'...")
            os.chdir(src_dir)
            exitcode = subprocess.call(["npm", "install"])
            if exitcode > 0:
                raise BuildException("Unable to install NodeJS packages. Exit code: {1}".format(exitcode))

        # If there is a gulpfile present, run 'gulp'
        if os.path.isfile("{0}/gulpfile.js".format(src_dir)):
            _logger.info("Found 'gulpfile.js', running 'gulp'...")
            os.chdir(src_dir)
            exitcode = subprocess.call(["gulp"])
            if exitcode > 0:
                raise BuildException("Unable to generate CSS/JS. Exit code: {1}".format(exitcode))


class BuildModuleJobHandler(BuildJobHandler):
    def build(self):
        _logger.info("Building {0} '{1}' [job id: {2}]".format(self.type, self.name, self.job_id))

        # Remember our main working space and create a new temporary working space
        work_dir = os.getcwd()
        tmp_dir = tempfile.mkdtemp()

        # Clear down artefact folder
        artefact_dir = get_artefact_dir(work_dir)
        _logger.info("Clearing down artefact folder ({0})...".format(artefact_dir))
        if os.path.isdir(artefact_dir):
            shutil.rmtree(artefact_dir)
        os.makedirs(artefact_dir)

        # Copy everything to be deployed into a folder in the tmpdir
        # (uses tar to leverage exclude patterns)
        tmp_build_dir = "{0}/{1}".format(tmp_dir, self.name)
        tar_file = "{0}/{1}.tar".format(tmp_dir, self.name)
        _logger.info("Reading from source with non-distribution files excluded ({0})...".format(work_dir))
        os.makedirs(tmp_build_dir)
        exitcode = subprocess.call([
            "tar", "cf", tar_file,
            "--exclude={0}".format(os.path.basename(artefact_dir)),
            "--exclude=Jenkinsfile",
            "--exclude=package-lock.json",
            "--exclude=.git*",
            "--exclude=*-env",
            "."
        ])
        if exitcode > 0:
            raise BuildException("Unable to create tar file for build copy. Exit code: {1}".format(exitcode))
        os.chdir(tmp_build_dir)
        _logger.info("Deploying copy to temporary build folder ({0})...".format(tmp_build_dir))
        exitcode = subprocess.call(["tar", "xf", tar_file])
        if exitcode > 0:
            raise BuildException("Unable to extract files from tar file into place. Exit code: {1}".format(exitcode))
        os.unlink(tar_file)

        # If there is a gulpfile present, run 'gulp'
        self.check_and_run_gulpfile(tmp_build_dir)

        # Zip it on up
        zip_file = "{0}/{1}.zip".format(get_artefact_dir(work_dir), self.name)
        _logger.info("Zipping up build folder to '{0}'...".format(zip_file))
        os.chdir(tmp_dir)
        exitcode = subprocess.call(["zip", "-r", zip_file, self.name,
            "-x", "*/node_modules/*"])
        if exitcode > 0:
            raise BuildException("Unable to move {0} into place. Exit code: {1}".format(self.type, exitcode))

        # Clear down temporary file amd folder
        os.chdir(work_dir)
        shutil.rmtree(tmp_dir)

        _logger.info("Done")


class BuildSiteJobHandler(BuildJobHandler):
    def __init__(self, config):
        self.config = config
        super(BuildSiteJobHandler, self).__init__("site", config['id'])

    def build(self):
        _logger.info("Building site '{0}' [job id: {1}]".format(self.name, self.job_id))

        # Clear down old build directory
        src_dir = os.getcwd()
        build_dir = "{0}/build".format(src_dir)
        if os.path.isdir(build_dir):
            shutil.rmtree(build_dir)
        work_dir = os.getcwd()
        os.makedirs(build_dir)
        os.chdir(build_dir)

        # Download and deploy WordPess
        if 'core' in self.config:
            self.install_core(build_dir)

        # Download and deploy listed themes
        if 'themes' in self.config:
            _logger.info("Building WordPress themes...")
            themes_dir = "{0}/wordpress/wp-content/themes".format(build_dir)
            for theme_url in self.config['themes']:
                self.install_theme(theme_url, themes_dir)

        # Download and deploy 'must-use' listed plugins
        if 'mu-plugins' in self.config:
            _logger.info("Building WordPress 'must-use' plugins...")
            plugins_dir = "{0}/wordpress/wp-content/mu-plugins".format(build_dir)
            for plugin_url in self.config['mu-plugins']:
                self.install_plugin(plugin_url, plugins_dir)

            # Adding must-use plugin autoloader
            # (see https://codex.wordpress.org/Must_Use_Plugins)
            _logger.info("Deploying must-use plugin autoloader to temporary build folder...")
            src_file = "{0}/extras/mu-autoloader.php".format(sys.prefix)
            dst_file = "{0}/wordpress/wp-content/mu-plugins/mu-autoloader.php".format(build_dir)
            try:
                shutil.copyfile(src_file, dst_file)
            except IOError as e:
                raise BuildException("Unable to copy must-use plugin autoloader into place: {0}".format(str(e)))

        # Download and deploy listed plugins
        if 'plugins' in self.config:
            _logger.info("Building WordPress plugins...")
            plugins_dir = "{0}/wordpress/wp-content/plugins".format(build_dir)
            for plugin_url in self.config['plugins']:
                self.install_plugin(plugin_url, plugins_dir)

        # Download and deploy listed development plugins if on develop branch
        if 'development-plugins' in self.config and is_develop_branch():
            _logger.info("Building WordPress development plugins...")
            plugins_dir = "{0}/wordpress/wp-content/plugins".format(build_dir)
            for plugin_url in self.config['development-plugins']:
                self.install_plugin(plugin_url, plugins_dir)

        # Copy in various other optional files that should also be deployed
        # (TODO: to be replaced by simpler 'deploy-files' folder approach)
        os.chdir(work_dir)
        extra_files = [
            'wp-config.php', 'favicon.ico', '.htaccess', 'robots.txt',
        ]
        if 'extra-files' in self.config:
            extra_files = self.config['extra-files']
        for filename in extra_files:
            if not os.path.isfile(filename):
                continue
            _logger.info("Deploying custom '{}' file to temporary build folder...".format(filename))
            dst_filename = "{0}/wordpress/{1}".format(build_dir, filename)
            try:
                shutil.copyfile(filename, dst_filename)
            except IOError as e:
                raise BuildException("Unable to copy '{}' into place: {}".format(filename, str(e)))

        # Special handling for cache drivers...
        cache_filename = "{0}/wordpress{1}".format(build_dir, "/wp-content/plugins/wp-super-cache/advanced-cache.php")
        if os.path.isfile(cache_filename):
            _logger.info("Copying WP Super Cache driver into place...")
            dst_filename = "{0}/wordpress{1}".format(build_dir, "/wp-content/advanced-cache.php")
            shutil.copyfile(cache_filename, dst_filename)

        # If there is a gulpfile present, run 'gulp'
        self.check_and_run_gulpfile(src_dir)

        # Set our file/directory permissions to be readable, to avoid perms issues later
        _logger.info("Resetting file/directory permissions in build folder...")
        for root, dirs, files in os.walk(build_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o644)

        # If we have custom directories, move things into their expected places
        if 'custom-directory-paths' in self.config:
            cdp = self.config['custom-directory-paths']
            if 'plugin-dir' in cdp:
                old_dir = "{0}/wordpress{1}".format(build_dir, "/wp-content/plugins")
                new_dir = "{0}/wordpress{1}".format(build_dir, cdp['plugin-dir'])
                os.rename(old_dir, new_dir)
                _logger.info("Moved plugins folder from '/wp-content/plugins' to {0}".format(cdp['plugin-dir']))
            if 'content-dir' in cdp:
                old_dir = "{0}/wordpress{1}".format(build_dir, "/wp-content")
                new_dir = "{0}/wordpress{1}".format(build_dir, cdp['content-dir'])
                os.rename(old_dir, new_dir)
                _logger.info("Moved content folder from '/wp-content' to {0}".format(cdp['content-dir']))

        _logger.info("Done")

    def install_core(self, build_dir):
        """Download and deploy a copy of WordPress to the build folder."""

        os.chdir("/tmp")

        # Fetch core
        core_url = self.config['core']['url']
        filename = os.path.basename(core_url)
        _logger.info("Fetching WordPress core from '{0}'...".format(core_url))
        exitcode = subprocess.call(["curl", "--retry", "3", "-sSL", "-o", filename, core_url])
        if exitcode > 0:
            raise BuildException("Unable to download Wordpress. Exit code from curl: {0}".format(exitcode))

        # Unpack core, except for default themes and plugins
        _logger.info("Unpacking WordPress core '{0}'...".format(filename))
        os.chdir(build_dir)
        zipfilename = "/tmp/{0}".format(os.path.basename(core_url))
        exitcode = subprocess.call(["tar", "-xzf", zipfilename,
            "--exclude=wordpress/wp-content/plugins/*",
            "--exclude=wordpress/wp-content/themes/*"
        ])
        if exitcode > 0:
            raise BuildException("Unable to unpack Wordpress. Exit code from 'tar': {0}".format(exitcode))

        # If themes/plugins folders are now missing, create empty ones.
        for dir in ['plugins', 'themes']:
            if not os.path.isdir('wordpress/wp-content/' + dir):
                os.mkdir('wordpress/wp-content/' + dir)

        # Clear down temporary file
        os.unlink(zipfilename)


    def _install_thing(self, url, dest_dir):
        """Download and deploy a copy of a WordPress theme or plugin to the build folder."""

        os.chdir("/tmp")

        # Fetch thing
        zipfilename = "/tmp/{0}".format(os.path.basename(url))
        name = os.path.basename(url).replace(".zip", "")
        _logger.info("Fetching WordPress {0} '{1}' from '{2}'...".format(self.type, name, url))
        exitcode = subprocess.call(["curl", "--retry", "3", "-sSL", "-o", zipfilename, url])
        if exitcode > 0:
            raise BuildException("Unable to download {0}. Exit code: {1}".format(self.type, exitcode))

        # Create a temporary working space
        tmp_dir = tempfile.mkdtemp()
        os.chdir(tmp_dir)

        # Unpack thing
        _logger.info("Unpacking WordPress {0} '{1}'...".format(self.type, name))
        exitcode = subprocess.call(["unzip", "-qo", zipfilename])
        if exitcode > 0:
            raise BuildException("Unable to unpack {0}. Exit code: {1}".format(self.type, exitcode))

        # Ignore various directories that are included in some distros (e.g. seedprod)
        unpacked_dir = None
        folders = os.listdir(tmp_dir)
        for folder in folders:
            if folder not in ['__MACOSX', '.DS_Store']:
                unpacked_dir = folder
                break
        if unpacked_dir is None:
            raise BuildException("Unable to identify main {0} folder in download.".format(self.type))

        # Move thing into place
        _logger.info("Moving WordPress {0} '{1}' into place...".format(self.type, name))
        exitcode = subprocess.call(["mv", unpacked_dir, dest_dir])
        if exitcode > 0:
            raise BuildException("Unable to move {0} into place. Exit code: {1}".format(self.type, exitcode))

        # Clear down temporary file amd folder
        os.unlink(zipfilename)
        shutil.rmtree(tmp_dir)

    def install_plugin(self, url, dir):
        self._install_thing(url, dir)

    def install_theme(self, url, dir):
        self._install_thing(url, dir)


def build_plugin(args):
    module_id = os.getenv("JOB_BASE_NAME", os.path.basename(os.getcwd()))
    job = BuildModuleJobHandler("plugin", module_id)
    return job._build_handling_exceptions()

def build_theme(args):
    module_id = os.getenv("JOB_BASE_NAME", os.path.basename(os.getcwd()))
    job = BuildModuleJobHandler("theme", module_id)
    return job._build_handling_exceptions()

def build_site(args):
    # Read configuration file
    with open("config.yml", 'r') as s:
        try:
            config = yaml.load(s)
        except yaml.YAMLError as e:
            _logger.error(e)
            return 1

    job = BuildSiteJobHandler(config)
    return job._build_handling_exceptions()
