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
from .notifications import *


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
            notify_start("build")
            self.build()
            notify_success("build")
            return 0
        except Exception as e:
            _logger.exception(str(e))
            self._handle_exception(e)
            notify_failure("build", str(e))
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
    def __init__(self, config, args):
        self.config = config
        self.args = args
        super(BuildSiteJobHandler, self).__init__("site", None, args)

    def build(self):
        _logger.info("Building site '{0}' [job id: {1}]".format(self.name, self.job_id))

        # Clear down root build directory
        src_dir = os.getcwd()
        root_build_dir = "{0}/build".format(src_dir)
        if os.path.isdir(root_build_dir):
            shutil.rmtree(root_build_dir)

        # First, make lists of unique core, theme and plugins to be downloaded
        # so we only download them once each
        dl_core = set()
        dl_themes = set()
        dl_plugins = set()
        for build_ref in self.config['builds'].keys():
            build_spec = self.config['builds'][build_ref]
            dl_core = dl_core.union([build_spec['core'], ])
            for layer_ref in build_spec['layers']:
                if 'themes' in self.config['layers'][layer_ref]:
                    dl_themes = dl_themes.union(self.config['layers'][layer_ref]['themes'])
                if 'plugins' in self.config['layers'][layer_ref]:
                    dl_plugins = dl_plugins.union(self.config['layers'][layer_ref]['plugins'])
                if 'mu-plugins' in self.config['layers'][layer_ref]:
                    dl_plugins = dl_plugins.union(self.config['layers'][layer_ref]['mu-plugins'])
        _logger.info("Identified {0} core versions, {1} unique themes and {2} unique plugins...".format(
            len(dl_core),
            len(dl_themes),
            len(dl_plugins),
        ))

        # Create base build directories for each build
        for build_ref in self.config['builds'].keys():
            build_dir = "{0}/build/{1}".format(src_dir, build_ref)
            os.makedirs(build_dir)

        # Download and deploy WordPess core version(s)
        for core_url in dl_core:
            # Download core
            self.fetch_core(core_url)

            # Identify which builds use this core
            for build_ref in self.config['builds'].keys():
                build_spec = self.config['builds'][build_ref]
                if build_spec['core'] == core_url:
                    build_dir = "{0}/build/{1}".format(src_dir, build_ref)
                    self.install_core(core_url, build_dir)

        # Download and deploy themes
        for theme_url in dl_themes:
            # Download theme
            self.fetch_theme(theme_url)

            # Identify which builds use this theme
            build_dirs = []
            for build_ref in self.config['builds'].keys():
                build_spec = self.config['builds'][build_ref]
                for layer_ref in build_spec['layers']:
                    if 'themes' in self.config['layers'][layer_ref]:
                        layer_themes = self.config['layers'][layer_ref]['themes']
                        if theme_url in layer_themes:
                            build_dirs.append("{0}/build/{1}/wordpress/wp-content/themes".format(src_dir, build_ref))
            if len(build_dirs) > 0:
                self.install_theme(theme_url, build_dirs)

        # Download and deploy plugins
        mu_plugin_build_refs = []
        for plugin_url in dl_plugins:
            # Download plugin
            self.fetch_plugin(plugin_url)

            # Identify which builds use this (ordinary/must-use) plugin
            build_dirs = []
            for build_ref in self.config['builds'].keys():
                build_spec = self.config['builds'][build_ref]
                for layer_ref in build_spec['layers']:
                    if 'plugins' in self.config['layers'][layer_ref]:
                        layer_plugins = self.config['layers'][layer_ref]['plugins']
                        if plugin_url in layer_plugins:
                            build_dirs.append("{0}/build/{1}/wordpress/wp-content/plugins".format(src_dir, build_ref))
                    if 'mu-plugins' in self.config['layers'][layer_ref]:
                        layer_plugins = self.config['layers'][layer_ref]['mu-plugins']
                        if plugin_url in layer_plugins:
                            build_dirs.append("{0}/build/{1}/wordpress/wp-content/mu-plugins".format(src_dir, build_ref))
                            mu_plugin_build_refs.append(build_ref)
            if len(build_dirs) > 0:
                self.install_plugin(plugin_url, build_dirs)

        # If there are 'must-use' plugins in builds...
        if len(mu_plugin_build_refs) > 0:
            _logger.info("Deploying must-use plugin autoloaders...")
            for build_ref in mu_plugin_build_refs:
                # Adding must-use plugin autoloader
                # (see https://codex.wordpress.org/Must_Use_Plugins)
                _logger.debug("Deploying must-use plugin autoloader for '{0}' build...".format(build_ref))
                src_file = "{0}/extras/mu-autoloader.php".format(sys.prefix)
                dst_file = "{0}/build/{1}/wordpress/wp-content/mu-plugins/mu-autoloader.php".format(src_dir, build_ref)
                try:
                    shutil.copyfile(src_file, dst_file)
                except IOError as e:
                    raise BuildException("Unable to copy must-use plugin autoloader into place: {0}".format(str(e)))

        # Copy in various other optional files that should also be deployed
        # (TODO: to be replaced by simpler 'deploy-files' folder approach)
        os.chdir(src_dir)
        extra_files = [
            'wp-config.php', 'favicon.ico', '.htaccess', 'robots.txt',
        ]
        if 'extra-files' in self.config:
            extra_files = self.config['extra-files']
        for filename in extra_files:
            if not os.path.isfile(filename):
                continue
            _logger.info("Deploying custom '{}' file to temporary build folder...".format(filename))
            for build_ref in self.config['builds'].keys():
                dst_filename = "{0}/build/{1}/wordpress/{2}".format(src_dir, build_ref, filename)
                try:
                    shutil.copyfile(filename, dst_filename)
                except IOError as e:
                    raise BuildException("Unable to copy '{}' into place: {}".format(filename, str(e)))

        # Special handling for WP Super Cache driver...
        for build_ref in self.config['builds'].keys():
            cache_filename = "{0}/build/{1}/wordpress/wp-content/plugins/wp-super-cache/advanced-cache.php".format(src_dir, build_ref)
            if not os.path.isfile(cache_filename):
                continue
            _logger.info("Copying WP Super Cache driver into place for build '{0}'...".format(build_ref))
            dst_filename = "{0}/build/{1}/wordpress/wp-content/advanced-cache.php".format(src_dir, build_ref)
            try:
                shutil.copyfile(cache_filename, dst_filename)
            except IOError as e:
                raise BuildException("Unable to copy '{}' into place: {}".format(cache_filename, str(e)))

        # If there is a 'package.json' present, run 'npm install' (prep for 'gulp')
        if os.path.isfile("{0}/package.json".format(src_dir)):
            _logger.info("Found 'package.json', running 'npm install'...")
            os.chdir(src_dir)
            exitcode = subprocess.call(["npm", "install"])
            if exitcode > 0:
                raise BuildException("Unable to install NodeJS packages. Exit code: {1}".format(exitcode))

        # If there is a gulpfile present, run 'gulp' for each build
        if os.path.isfile("{0}/gulpfile.js".format(src_dir)):
            _logger.info("Found 'gulpfile.js', running 'gulp'...")
            os.chdir(src_dir)
            for build_ref in self.config['builds'].keys():
                exitcode = subprocess.call(["gulp"], env={'BUILD_REF': build_ref})
                if exitcode > 0:
                    raise BuildException("Unable to generate CSS/JS with gulp. Exit code: {1}".format(exitcode))

        # Set our file/directory permissions to be readable, to avoid perms issues later
        _logger.info("Resetting file/directory permissions in build folder...")
        for root, dirs, files in os.walk(build_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o644)

        _logger.info("Done")

    def fetch_core(self, core_url):
        """Download and deploy a copy of WordPress to the build folder."""

        # Fetch core
        filename = "/tmp/{0}".format(os.path.basename(core_url))
        _logger.info("Fetching WordPress core from '{0}'...".format(core_url))
        exitcode = subprocess.call(["curl", "--retry", "3", "-sSL", "-o", filename, core_url])
        if exitcode > 0:
            raise BuildException("Unable to download Wordpress. Exit code from curl: {0}".format(exitcode))

    def install_core(self, core_url, build_dir):
        """Deploy a copy of the specific WordPress version to the given build folder."""

        # Unpack core, except for default themes and plugins
        _logger.debug("Unpacking WordPress core '{0}' to build '{1}'...".format(
            os.path.basename(core_url),
            os.path.basename(build_dir)
        ))
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


    def _fetch_thing(self, type, url):
        """Download a copy of a WordPress theme or plugin to a temporary area."""

        # Fetch thing
        zipfilename = "/tmp/{0}".format(os.path.basename(url))
        name = os.path.basename(url).replace(".zip", "")
        _logger.info("Fetching WordPress {0} '{1}' from '{2}'...".format(type, name, url))
        exitcode = subprocess.call(["curl", "--retry", "3", "-sSL", "-o", zipfilename, url])
        if exitcode > 0:
            raise BuildException("Unable to download {0} '{1}'. Exit code: {2}".format(type, name, exitcode))

    def fetch_plugin(self, url):
        self._fetch_thing("plugin", url)

    def fetch_theme(self, url):
        self._fetch_thing("theme", url)

    def _install_thing(self, url, dest_dirs):
        """Deploy a copy of a WordPress theme or plugin to the given folders."""

        # Create a temporary working space
        tmp_dir = tempfile.mkdtemp()
        os.chdir(tmp_dir)

        # Unpack thing
        name = os.path.basename(url).replace(".zip", "")
        _logger.debug("Unpacking '{0}'...".format(name))
        zipfilename = "/tmp/{0}".format(os.path.basename(url))
        exitcode = subprocess.call(["unzip", "-qo", zipfilename])
        if exitcode > 0:
            raise BuildException("Unable to unpack '{0}'. Exit code: {1}".format(name, exitcode))

        # Ignore various directories that are included in some distros (e.g. seedprod)
        unpacked_dir = None
        folders = os.listdir(tmp_dir)
        for folder in folders:
            if folder not in ['__MACOSX', '.DS_Store']:
                unpacked_dir = tmp_dir + "/" + folder
                break
        if unpacked_dir is None:
            raise BuildException("Unable to identify main folder in '{0}' download.".format(name))

        # Copy thing into place for each dest dir
        for dest_dir in dest_dirs:
            _logger.debug("Copying '{0}' to {1}...".format(name, dest_dir))
            exitcode = subprocess.call(["cp", "-r", unpacked_dir, dest_dir])
            if exitcode > 0:
                raise BuildException("Unable to copy '{0}' into place. Exit code: {1}".format(name, exitcode))

        # Clear down temporary file amd folder
        shutil.rmtree(tmp_dir)

    def install_plugin(self, url, dir):
        self._install_thing(url, dir)

    def install_theme(self, url, dir):
        self._install_thing(url, dir)


def build_plugin(args):
    module_id = os.getenv("JOB_BASE_NAME", os.path.basename(os.getcwd()))
    job = BuildModuleJobHandler("plugin", module_id, args)
    return job._build_handling_exceptions()

def build_theme(args):
    module_id = os.getenv("JOB_BASE_NAME", os.path.basename(os.getcwd()))
    job = BuildModuleJobHandler("theme", module_id, args)
    return job._build_handling_exceptions()

def build_site(args):
    # Read build configuration file
    with open("build.yml", 'r') as s:
        try:
            config = yaml.load(s)
        except yaml.YAMLError as e:
            _logger.error(e)
            return 1

    job = BuildSiteJobHandler(config, args)
    return job._build_handling_exceptions()
