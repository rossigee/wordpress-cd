#!/usr/bin/env python
#
# Build script.
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


def check_and_run_gulpfile(src_dir):
    # If there is a 'package.json' present, run 'npm install'
    if os.path.isfile("{0}/package.json".format(src_dir)):
        _logger.info("Found 'package.json', running 'npm install'...")
        os.chdir(src_dir)
        exitcode = subprocess.call(["npm", "install"])
        if exitcode > 0:
            _logger.error("Unable to install NodeJS packages. Exit code: {1}".format(exitcode))
            return exitcode

    # If there is a gulpfile present, run 'gulp'
    if os.path.isfile("{0}/gulpfile.js".format(src_dir)):
        _logger.info("Found 'gulpfile.js', running 'gulp'...")
        os.chdir(src_dir)
        exitcode = subprocess.call(["gulp"])
        if exitcode > 0:
            _logger.error("Unable to generate CSS/JS. Exit code: {1}".format(exitcode))
            return exitcode

    return 0

def _build_module(module_type):
    module_id = os.getenv("JOB_BASE_NAME", os.path.basename(os.getcwd()))
    _logger.info("Building WordPress {0} {1}...".format(module_type, module_id))

    # Remember our main working space and create a new temporary working space
    work_dir = os.getcwd()
    tmp_dir = tempfile.mkdtemp()

    # Clear down artefact folder
    _logger.info("Clearing down artefact folder...")
    artefact_dir = get_artefact_dir(work_dir)
    if os.path.isdir(artefact_dir):
        shutil.rmtree(artefact_dir)
    os.makedirs(artefact_dir)

    # Copy everything to be deployed into a folder in the tmpdir
    # (uses tar to leverage exclude patterns)
    _logger.info("Deploying copy to temporary build folder...")
    tar_file = "{0}/{1}.tar".format(tmp_dir, module_id)
    exitcode = subprocess.call([
        "tar", "cf", tar_file, ".",
        "--exclude=Jenkinsfile",
        "--exclude=package-lock.json",
        "--exclude=.git*",
        "--exclude=*-env",
    ])
    if exitcode > 0:
        _logger.error("Unable to create tar file for build copy. Exit code: {1}".format(exitcode))
        return exitcode
    tmp_build_dir = "{0}/{1}".format(tmp_dir, module_id)
    os.makedirs(tmp_build_dir)
    os.chdir(tmp_build_dir)
    exitcode = subprocess.call(["tar", "xf", tar_file])
    if exitcode > 0:
        _logger.error("Unable to extract files from tar file into place. Exit code: {1}".format(exitcode))
        return exitcode
    os.unlink(tar_file)

    # If there is a gulpfile present, run 'gulp'
    exitcode = check_and_run_gulpfile(tmp_build_dir)
    if exitcode > 0:
        return exitcode

    # Zip it on up
    zip_file = "{0}/{1}.zip".format(get_artefact_dir(work_dir), module_id)
    _logger.info("Zipping up build folder to '{0}'...".format(zip_file))
    os.chdir(tmp_dir)
    exitcode = subprocess.call(["zip", "-r", zip_file, module_id,
        "-x", "*/node_modules/*"])
    if exitcode > 0:
        _logger.error("Unable to move {0} into place. Exit code: {1}".format(type, exitcode))
        return exitcode

    # Clear down temporary file amd folder
    os.chdir(work_dir)
    shutil.rmtree(tmp_dir)

    _logger.info("Done")

def get_artefact_dir(work_dir):
    # Determine where we're going to place the resulting ZIP file
    try:
        return "{0}/{1}".format(work_dir, os.environ['WPCD_ARTEFACT_DIR'])
    except KeyError:
        return "{0}/wpcd-artefacts".format(work_dir)

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

def build_plugin(args):
    return _build_module("plugin")

def build_theme(args):
    return _build_module("theme")

def install_core(config, build_dir):
    os.chdir("/tmp")

    # Fetch core
    core_url = config['core']['url']
    filename = os.path.basename(core_url)
    _logger.info("Fetching WordPress core from '{0}'...".format(core_url))
    exitcode = subprocess.call(["curl", "--retry", "3", "-sSL", "-o", filename, core_url])
    if exitcode > 0:
        _logger.error("Unable to download Wordpress. Exit code: {0}".format(exitcode))
        return exitcode

    # Unpack core, except for default themes and plugins
    _logger.info("Unpacking WordPress core '{0}'...".format(filename))
    os.chdir(build_dir)
    zipfilename = "/tmp/{0}".format(os.path.basename(core_url))
    exitcode = subprocess.call(["tar", "-xzf", zipfilename,
        "--exclude=wordpress/wp-content/plugins/*",
        "--exclude=wordpress/wp-content/themes/*"
    ])
    if exitcode > 0:
        _logger.error("Unable to unpack Wordpress. Exit code: {0}".format(exitcode))
        return exitcode

    # If themes/plugins folders are now missing, create empty ones.
    for dir in ['plugins', 'themes']:
        if not os.path.isdir('wordpress/wp-content/' + dir):
            os.mkdir('wordpress/wp-content/' + dir)

    # Clear down temporary file
    os.unlink(zipfilename)

    return 0

def _install_thing(url, type, dest_dir):
    os.chdir("/tmp")

    # Fetch thing
    zipfilename = "/tmp/{0}".format(os.path.basename(url))
    name = os.path.basename(url).replace(".zip", "")
    _logger.info("Fetching WordPress {0} '{1}' from '{2}'...".format(type, name, url))
    exitcode = subprocess.call(["curl", "--retry", "3", "-sSL", "-o", zipfilename, url])
    if exitcode > 0:
        _logger.error("Unable to download {0}. Exit code: {1}".format(type, exitcode))
        return exitcode

    # Create a temporary working space
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)

    # Unpack thing
    _logger.info("Unpacking WordPress {0} '{1}'...".format(type, name))
    exitcode = subprocess.call(["unzip", "-qo", zipfilename])
    if exitcode > 0:
        _logger.error("Unable to unpack {0}. Exit code: {1}".format(type, exitcode))
        return exitcode

    # Ignore various directories that are included in some distros (seedprod)
    unpacked_dir = None
    folders = os.listdir(tmp_dir)
    for folder in folders:
        if folder not in ['__MACOSX', '.DS_Store']:
            unpacked_dir = folder
            break
    if unpacked_dir is None:
        _logger.error("Unable to identify {0} folder.".format(type))
        return exitcode

    # Move thing into place
    _logger.info("Moving WordPress {0} '{1}' into place...".format(type, name))
    exitcode = subprocess.call(["mv", unpacked_dir, dest_dir])
    if exitcode > 0:
        _logger.error("Unable to move {0} into place. Exit code: {1}".format(type, exitcode))
        return exitcode

    # Clear down temporary file amd folder
    os.unlink(zipfilename)
    shutil.rmtree(tmp_dir)

    return 0

def install_theme(theme, dest_dir):
    return _install_thing(theme, "theme", dest_dir)

def install_plugin(plugin, dest_dir):
    return _install_thing(plugin, "plugin", dest_dir)

def build_site(args):
    # Read configuration file
    with open("config.yml", 'r') as s:
        try:
            config = yaml.load(s)
        except yaml.YAMLError as e:
            _logger.error(e)
            return 1

    # Clear down old build directory
    src_dir = os.getcwd()
    build_dir = "{0}/build".format(src_dir)
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    work_dir = os.getcwd()
    os.makedirs(build_dir)
    os.chdir(build_dir)

    # Download and deploy WordPess
    if 'core' in config:
        exitcode = install_core(config, build_dir)
        if exitcode > 0:
            return exitcode

    # Download and deploy listed themes
    if 'themes' in config:
        _logger.info("Building WordPress themes...")
        themes_dir = "{0}/wordpress/wp-content/themes".format(build_dir)
        for theme in config['themes']:
            exitcode = install_theme(theme, themes_dir)
            if exitcode > 0:
                return exitcode

    # Download and deploy 'must-use' listed plugins
    if 'mu-plugins' in config:
        _logger.info("Building WordPress 'must-use' plugins...")
        plugins_dir = "{0}/wordpress/wp-content/mu-plugins".format(build_dir)
        for plugin in config['mu-plugins']:
            exitcode = install_plugin(plugin, plugins_dir)
            if exitcode > 0:
                return exitcode

        # Adding must-use plugin autoloader
        # (see https://codex.wordpress.org/Must_Use_Plugins)
        _logger.info("Deploying must-use plugin autoloader to temporary build folder...")
        src_file = "{0}/extras/mu-autoloader.php".format(sys.prefix)
        dst_file = "{0}/wordpress/wp-content/mu-plugins/mu-autoloader.php".format(build_dir)
        try:
            shutil.copyfile(src_file, dst_file)
        except IOError as e:
            _logger.error("Unable to copy must-use plugin autoloader into place: {0}".format(str(e)))
            return exitcode

    # Download and deploy listed plugins
    if 'plugins' in config:
        _logger.info("Building WordPress plugins...")
        plugins_dir = "{0}/wordpress/wp-content/plugins".format(build_dir)
        for plugin in config['plugins']:
            exitcode = install_plugin(plugin, plugins_dir)
            if exitcode > 0:
                return exitcode

    # Download and deploy listed development plugins if on develop branch
    if 'development-plugins' in config and is_develop_branch():
        _logger.info("Building WordPress development plugins...")
        plugins_dir = "{0}/wordpress/wp-content/plugins".format(build_dir)
        for plugin in config['development-plugins']:
            exitcode = install_plugin(plugin, plugins_dir)
            if exitcode > 0:
                return exitcode

    # Copy in various other optional files that should also be deployed
    os.chdir(work_dir)
    extra_files = [
        'wp-config.php', 'favicon.ico', '.htaccess', 'robots.txt',
    ]
    if 'extra-files' in config:
        extra_files = config['extra-files']
    for filename in extra_files:
        if not os.path.isfile(filename):
            continue
        _logger.info("Deploying custom '{}' file to temporary build folder...".format(filename))
        dst_filename = "{0}/wordpress/{1}".format(build_dir, filename)
        try:
            shutil.copyfile(filename, dst_filename)
        except IOError as e:
            _logger.error("Unable to copy '{}' into place: {}".format(filename, str(e)))
            return exitcode

    # Special handling for cache drivers...
    cache_filename = "{0}/wordpress{1}".format(build_dir, "/wp-content/plugins/wp-super-cache/advanced-cache.php")
    if os.path.isfile(cache_filename):
        _logger.info("Copying WP Super Cache driver into place...")
        dst_filename = "{0}/wordpress{1}".format(build_dir, "/wp-content/advanced-cache.php")
        shutil.copyfile(cache_filename, dst_filename)

    # If there is a gulpfile present, run 'gulp'
    exitcode = check_and_run_gulpfile(src_dir)
    if exitcode > 0:
        return exitcode

    # Set our file/directory permissions to be readable, to avoid perms issues later
    _logger.info("Resetting file/directory permissions in build folder...")
    for root, dirs, files in os.walk(build_dir):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for f in files:
            os.chmod(os.path.join(root, f), 0o644)

    # If we have custom directories, move things into their expected places
    if 'custom-directory-paths' in config:
        cdp = config['custom-directory-paths']
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
