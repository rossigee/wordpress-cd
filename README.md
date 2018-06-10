# WordPress Continuous Deployment/Delivery scripts

These scripts are designed to be called as part of the post-commit hook in Git repositories.

Currently tested with:

* GitLab
* Jenkins

I also use the 'build-wp-site' script locally to quickly generate clean builds with certain plugins/themes pre-installed, and use that to kick-start a local development environment.


## Installing the scripts

Install scripts using `pip`:

```
pip install wordpress-cd
```

Or, if deploying from source:

```
python setup.py install
```

Standard stuff. Use 'virtualenv' if you wish.


## Building a WordPress site

First, we define a site configuration by creating a 'config.yml' file.

A sample 'config.yml' file might look like this:

```yaml
# Identifier string that can be used by deployment drivers if required.
id: clubwebsite1

# The main application zipfile to base a build on.
core:
  url: https://wordpress.org/wordpress-4.9.4.tar.gz
  # or perhaps...
  url: https://wordpress.org/wordpress-latest.tar.gz

# List of themes to download and build into the document root
themes:
  - https://downloads.wordpress.org/themes/mobile.zip
  - https://gitlab.com/youraccount/wordpress/themes/acmeltd-theme/repository/master/archive.zip
  - https://s3-eu-west-1.amazonaws.com/yourbucket/production/mobile-child.zip

# 'Must use' plugins
mu-plugins:
  - https://downloads.wordpress.org/plugin/wp-bcrypt.zip

# Ordinary plugins
plugins:
  - https://downloads.wordpress.org/plugin/plugin-groups.zip
  - https://downloads.wordpress.org/plugin/acme-wp-plugin.zip
  - https://downloads.wordpress.org/plugin/another-plugin.zip

# Extra plugins to be installed when branch being deployed begins with 'develop'
development-plugins:
  - https://downloads.wordpress.org/plugin/debug-tools.zip

# Optional: To put a specific favicon.ico file into place
favicon:
  file: favicon.ico

```

To build a document root that contains a fresh WordPress instance with those themes and plugins installed:

```bash
build-wp-site -v
```

The resulting document root will now exist in the 'build/wordpress' folder.

## Deploying the site

As long as the necessary environment variables are set, it's just a case of running the site deploy script.

```bash
deploy-wp-site -v
```

This script will use the configured deployment driver to deploy the site.

The script needs to know a few things, defined by environment variables. Typically, these variables will be provided by the CI system that's running the script. You can also use the script locally by providing the same environment variables.

Env var | Description | Example value
--------|-------------|--------------
WPCD_JOB_NAME | Typically the short string name of the project/repo being deployed | `acme-widget`
WPCD_GIT_BRANCH | Which branch this is a build of, to help determine which environment to deploy to. | `master` (or `develop`)
WPCD_DRIVERS | Which python modules to import to register the necessary deployment drivers (may load multiple drivers) | `wordpress_cd.drivers.rsync`
WPCD_PLATFORM | Which driver id to use to perform the deployment | `rsync`

The above are the default environment variables used. The deploy script will attempt to identify which CI system is running and use the environment variables specific to that system if found.


### Deployment with rsync

This package comes with a simple 'rsync' based deployment driver. The main environment variables you need to set for a typical rsync deployment are:

Env var | Description | Example value
--------|-------------|--------------
SSH_HOST | Host to rsync to | www.myhost.com
SSH_PORT |

## Using an alternative deployment driver

You can tell the deployment script to import packages containing alternative deployment drivers by listing the modules to import (comma-seperated) in the `WORDPRESS_CD_DRIVERS` environment variable.

```bash
pip install wordpress-cd-rancher
export WPCD_DRIVERS=wordpress_cd_rancher
export WPCD_PLATFORM=rancher

export WORDPRESS_BEANSTALK_APP_ID=foo
export WORDPRESS_BEANSTALK_ENV_ID=bar
#...other specific variables/creds...
deploy-wp-site -v
```

NOTE: the above package is a fictional example. I might implement it one day.


## Integration with CI/CD systems

### GitLab

The deployment script can detect that it is being run in GitLab by the existence of [environment variables]() beginning with 'CI_'.

An example '.gitlab-ci.yml' for a site repository stored on GitLab might look like this:

```yaml
stages:
  - build
  - test
  - deploy

image: registry.gitlab.com/your-organisation/wordpress-cd

before_script:
  - aws s3 sync s3://your-gitlab-ci-bucket/ssh /root/.ssh && chmod 400 /root/.ssh/id_rsa
```

The S3 sync command ensures that the latest SSH public/private keys are available to commands being run in the container, without actually distributing those keys in the container image.

### Example workflow for a plugin

The '.gitlab-ci.yml' file might continue like this:

```yaml
build:
  stage: build
  tags:
    - docker
  script:
    - build-wp-plugin
  artifacts:
    paths:
    - build/*.zip
```

This tells Gitlab to use the 'build-wp-plugin' script to package up the code, which will create a ZIP file in the build folder, and to store this ZIP file as an artifact for later reference.

The following environment variables can be used to adjust the build behaviour.

Env var | Description | Example value
--------|-------------|--------------
WPCD_ARTEFACT_DIR | Which subfolder of the source directory to create and use for build artefacts | `wpcd-artefacts`

[TODO] There should then be one or more 'test' stages, which will trigger third-party integration, regression, unit test and UI/UX pipelines and process their success/failure responses accordingly.

Once built and tested, the ZIP can then be deployed. The 'deploy-wp-plugin' script derives the target of the deployment from the stage name. The format is roughly:

```
deploy:<platform>:<site>:<site>:
```

In the case of production builds, triggered by commits to the 'master' branch, the following configuration will ensure that a copy of the ZIP is placed in our S3 archive, which is then pointed to from the plugins list in our site configurations, and used in subsequent production site builds.

```yaml
deploy:aws:s3:production:
  stage: deploy
  only:
    - master
  tags:
    - docker
  environment:
    name: aws-s3-production-plugins-bucket
  script:
    - deploy-wp-plugin
```

In the case of development builds, triggered by commits to the 'develop' branch, the following configuration can be used to install/replace the plugin on the 'site1' site, hosted on the 'development2' server on Cloudways:

```yaml
deploy:cloudways:development2:site1:
  stage: deploy
  only:
    - develop
  tags:
    - docker
  environment:
    name: cloudways-development2-site1
    url: https://dev.yourdomain.com
  script:
    - deploy-wp-plugin
```

## Example for a site configuration repository

The beginning, build and test stages are exactly the same as for plugins, as described above, but using the 'build-wp-site' script instead of the 'build-plugin' script, and collecting the whole build folder as an artifact, instead of just the ZIP file. For example:

```yaml
build:
  stage: build
  tags:
    - docker
  script:
    - build-wp-site
  artifacts:
    paths:
    - build/
```

This works by reading a 'config.yml' file from the repo, and using the details provided to fetch a specific version of WordPress plus various public and private artifacts specified and assemble them into the build folder to form a full 'document root' snapshot. A sample 'config.yml' file might look like this:

```yaml
id: site1

core:
  url: https://wordpress.org/wordpress-4.9.4.tar.gz

themes:
  - https://downloads.wordpress.org/themes/maintheme.zip
  - https://gitlab.com/yourdomain/wordpress/themes/yourtheme-child/repository/master/archive.zip
  - https://s3.amazonaws.com/somebucket/production/another-child.zip

mu-plugins:
  - https://downloads.wordpress.org/plugin/wp-bcrypt.zip

plugins:
  - https://downloads.wordpress.org/plugin/plugin-groups.zip
  - https://downloads.wordpress.org/plugin/acme-wp-plugin.zip
  - https://downloads.wordpress.org/plugin/another-plugin.zip

```

The deploy stages also work in a similar way to plugins, as described above, but instead of using replacing just the plugin (or theme) on the target host, it uses 'rsync' to sync the latest build into place, ignoring only dynamic areas of the site (i.e. the 'wp-config.php' file, the 'wp-content/uploads' folder etc).

```yaml
.deploy:cloudways:development2:site1:
  stage: deploy
  only:
    - develop
  tags:
    - docker
  environment:
    name: cloudways-development2-site1
    url: https://dev.site1.yourdomain.com
  script:
    - deploy-wp-site
```


## Running locally for development/testing purpose

Create a 'staging-env' file, containing the following...

```bash
export CI_DRIVERS=cloudways

export CLOUDwAYS_API_EMAIL=(from_the_control_panel)
export CLOUDwAYS_API_KEY=(from_the_control_panel)

export AWS_ACCESS_KEY_ID=(your_aws_creds)
export AWS_SECRET_ACCESS_KEY=(your_aws_creds)
```

You'll see there are no SFTP passwords included here, as we're using public key auth for added security. The CI container fetches it's SSH keys from an S3 bucket at runtime. When run locally it will use your SSH keys by default.

Set up a python temporary virtual environment locally.

```bash
pip install virtualenv
virtualenv /tmp/ci-venv
. /tmp/ci-venv/bin/activate
pip install -r requirements.txt
python setup.py install
. staging-env
cd /your/dev/folder/acme-extension
build-wp-plugin
deploy-wp-plugin
```

If you prefer to use Docker, to build and run a fresh container:

```bash
docker build -t wordpress-ci .
docker run --rm -ti -v /your/wp/plugins/acme-extension:/acme-extension wordpress-ci sh
cd /acme-extension
. staging-env
build-wp-plugin
deploy-wp-plugin
```

You should now be able to run the theme tools from a theme repository, plugin tools from a plugin repository and host deployments from a host configuration repository.


## Building and deploying a theme or plugin

Replace 'theme' with 'plugin' as necessary in the following examples.

```bash
cd ~/workshop/themes/yourtheme
git checkout staging
build-wp-theme
deploy-wp-theme s3-staging
deploy-wp-theme cloudways-cms-staging
deploy-wp-theme cloudways-site1-staging
```

Or, within a docker container:

```bash
. staging-env
cd /acme-extension
build-wp-plugin
deploy-wp-plugin
```

The build stage checks for the presence of 'package.json' file and runs 'npm install' if found.

It also checks for a 'gulpfile.js', and runs 'gulp' if found. This presumes a default gulp target has been specified.


## Building and deploying a site template

```bash
cd ~/workshop/hosts/cms
git checkout staging
build-wp-site
deploy-wp-site s3-staging
deploy-wp-site cloudways-staging
```

Or, within a docker container:

```bash
. staging-env
cd /cms
build-wp-site
deploy-wp-site
```
