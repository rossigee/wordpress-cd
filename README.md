# WordPress Continuous Deployment/Delivery scripts

These scripts are designed to be called as part of the post-commit hook in Git repositories.

Currently tested with:

* GitLab
* Jenkins

They can also be a useful tool for local development. For example, I often use the `build-wp-site` script locally to quickly generate clean builds with certain plugins/themes pre-installed, and use that to kick-start a local development environment, using the build folder as the document root.

Often, this package is a dependency of a specific platform driver (i.e. Amazon Beanstalk, Azure EKS, Kubernetes, whatever), which is a dependency of an organisational package. Thus, an example inheritence chain would look like:

 * BaseDriver (from this package `wordpress_cd`)
 * RancherDriver (from third-party `wordpress_rancher` package)
 * AcmeWidgetsRancherDriver (a custom/proprietary package, which will contain organisation-specific extensions/overrides to the common workflow)

For example, the organisation-specific methods might override the setup and teardown methods for the DNS to use an internal nameserver for test hosts. Or include additional files in the `.ebextensions` folder of a Beanstalk application.


## Installing the scripts

The scripts can be installed using `pip`:

```
pip install wordpress-cd
```

Or, if deploying from source:

```
python setup.py install
```

Standard stuff. Use `virtualenv` if you wish.

The end result is that the following command line tools are available:

* `build-wp-site`
* `test-wp-site`
* `deploy-wp-site`

Each represents a typical high-level stage in a CI workflow.

Additionally, the following command line tools will be available:

* `build-wp-plugin`
* `test-wp-plugin`
* `deploy-wp-plugin`
* `build-wp-theme`
* `test-wp-theme`
* `deploy-wp-theme`

These allow CI workflows for specific themes/plugins to be developed, so a particular theme/plugin can be applied to a given site without having to rebuild and redeploy the whole docroot. It also allows for fresh build of plugins and themes to be deployed in readiness for inclusing in newly built sites.

NOTE: The `test-*` scripts for themes and plugins are just placeholders, as it's not usually practical to do end-to-end regression testing of WP plugins, and I've not come across any plugins that have their own unit tests yet.

### Dockerisation

These scripts can be installed directly on your Jenkins (or other) CI server. However, we find it best to use a custom CI build container that contains `wordpress_cd` plus all the platform drivers we use, plus the command-line tools they depend on (such as `zip`, `mysql`, `aws` etc.).

TODO: Workflow example.


## Building a WordPress site

First, create a working directory to contain your site configuration and related files.

Within that folder, we define a `config.yml` site configuration file listing the main 'ingredients' we want our document root build to consist of.

A sample `config.yml` file might look like this:

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

```

To build a document root that contains a fresh WordPress instance with that configuration:

```bash
build-wp-site -v
```

The resulting document root will now exist in the `build/wordpress` folder. The CI system should consider the `build` folder an artifact, as it will be expected by the subsequent testing and deployment stages.

TODO: It should probably also ZIP up document root, and provide the ZIP file, last commit message and a checksum value.


### URLs in the config file

The main components for the build are retrieved using `curl` as a subprocess. That means only simple 'http' or 'https' links are allowed for now.

TODO: Extend to accept `s3://` URLs for private plugin repositories hosted on the popular storage platform.

TODO: Extend to allow `envato://` (or other proprietary URL schemes) to allow the latest or specific versions of proprietary plugins or themes to be retrieved directly from their source repositories or vendor packaging system.


### Including a `wp-config.php` file

If there is a `wp-config.php` file present in the current working directory when the `build-wp-site` script is run, it is included in the build.

Typically, it's good practice to include a production-ready version of this config, but with the database settings retrieved from environment variables set by the production host.

```
define('DB_NAME', getenv("DB_NAME"));
define('DB_USER', getenv("DB_USER"));
define('DB_PASSWORD', getenv("DB_PASSWORD"));
define('DB_HOST', getenv("DB_HOST"));
```

Some people may prefer not to include a `wp-config.php` file at build time, but instead generate or include specific configs at testing and/or final deployment time.


### Including a `.htaccess` file

If there is a `.htaccess` file present in the current working directory when the `build-wp-site` script is run, it is included in the build.


### Including a `favicon.ico` file

If there is a `favicon.ico` file present in the current working directory when the `build-wp-site` script is run, it is included in the build.


## Testing the site

In order to 'clean room' test a site, it needs to be set up from scratch with a known set of data, and a series of tests run against the site. If all tests pass, we can proceed to the deployment stage.

As the test stage needs to orchestrate services on different hosting platform providers, it depends on 'drivers' (a.k.a. 'plugins' or 'modules') to perform the actual orchestration of hosting resources and related services.

NOTE: The same `deploy_site` method that deploys the document root to pre-configured transient test environments can also be used by the `deploy` stage to ship the build to a pre-existing production or staging environments. So the same driver is usually used by both the 'test' and 'deploy' CI stages.


### Platform drivers

There will be different drivers for different hosting platforms and techniques, which will be maintained seperately as python packages that depend on this one.

A driver will be a subclass of `BaseDriver` that implements the main stages involved in testing a WordPress site:

* `setup` - Running up a VM or virtualhost using the latest build, connecting it to a database containing a fresh snapshot of test data, adding a DNS entry for external access, applying an SSL certificate etc. and generally making a cleanroom instance available at a particular URL.
* `run_tests` - Invokes one or more internal or external profiling/testing tools against the newly created URL, gathering metrics/statistics/results for later presentation, including an overall pass/failure status.
* `teardown` - Revoking any generated temporary SSL certificates (if necessary), removing DNS entry, purging test database and releasing any other resources used by the test host.

TODO: Include an example within this package.

The following are existing `wordress_cd` driver implementations that may serve as a useful reference or base for new ones:

* [wordpress_cd_s3](https://github.com/rossigee/wordpress-cd-s3)
* [wordpress_cd_rancher](https://github.com/rossigee/wordpress-cd-rancher)


### Datasets

During the `setup` stage, drivers will need to obtain the datasets to be used for testing. Typically, there are juts two datasets:

* a gzipped SQL dump of a WordPress instance, and
* a gzipped tar file containing the sites `wp-content/uploads` folder.

How organisations prefer to make this data available at runtime will be determined by the 'dataset' class that the driver is configured to use. A 'dataset' is implemented as a `BaseDataSet` subclass.


### FileDataSet

(NOTE: This dataset is not ready yet)

If the datasets are to be made available as files to the test script at run-time (i.e. the script is run in the repo root, and the dump files are managed in the repo), then the `FileDateSet` class should be used. It will expect the files to exist in the current working directory, and be named specifically. Otherwise, the following environment variables can be used to override the settings.

Env var | Meaning | Default
--------|---------|--------
TEST_DATASET_ROOT | Folder containing test datasets | (working directory at runtime)
TEST_DATASET_SQL_DUMPFILE | Filename of compressed SQL dump | `test-database.sql.gz`
TEST_DATASET_UPLOADS_DUMPFILE | Filename of compressed tar of uploads folder | `test-uploads.sql.gz`

In some cases, these dump files will be available locally, either provided by the CI system, or kept in the repo the script is being run from.


### HTTPDataSet

(NOTE: This dataset is not ready yet)

If the datasets are to be hosted by an external web service and need to be collected dynamically via HTTP(/S), the `HTTPDataSet` class can be used.

Env var | Meaning | Default
--------|---------|--------
TEST_DATASET_SQL_URL | URL to use to collect compressed SQL dump | N/A
TEST_DATASET_UPLOADS_URL | URL to use to collect compressed tar of uploads folder | N/A


### S3DataSet

If the datasets are to be hosted on an S3 bucket, the `S3DataSet` class can be used.

This dataset implementation required the `boto3` library.

Env var | Meaning | Default
--------|---------|--------
AWS_ACCESS_KEY_ID | AWS credentials to use | N/A
AWS_SECRET_ACCESS_KEY | AWS credentials to use | N/A
TEST_DATASET_S3_URL | S3 bucket (and prefix) to retrieve datasets from (e.g. `s3://your-bucket-name/folder1`) | N/A


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
WPCD_DRIVERS | Which python modules to import to register the necessary deployment drivers (may load multiple drivers, comma-seperated) | `wordpress_cd.drivers.rsync`
WPCD_PLATFORM | Which driver id to use for testing or deployment | `rsync`

The above are the default environment variables used. The deploy script will attempt to identify which CI system is running and use the environment variables specific to that system if found.


### The supplied `rsync` driver

This package comes with a simple `rsync` based driver, that implements the deployment methods for modules (plugins and themes) and sites. The main environment variables you need to set for a typical rsync deployment are:

Env var | Description | Example value
--------|-------------|--------------
SSH_HOST | Host to rsync to | www.myhost.com
SSH_PORT | Port on server to connect to | 22
SSH_USER | Username to login with | roger
SSH_PASS | Password to login with | ramjet
SSH_PATH | Where document root can be found on remote server | `/home/u12345/public_html`

Module deployments will replace the module on the server.

Site deployments will replace the document root on the server, with a few exceptions:

* The `wp-config.php` file, which may contain necessary db credentials/prefixes etc.
* A `wp-salt.php` file, as this would break some sites which use a seperate salt file (not personally recommended).
* The `wp-content/uploads` folder, containing the site's media.

Other than those exception, anything else is in the document root that is not also in the build root will be destroyed, so configure with caution and keep backups to hand. If extra files are required (i.e. 'proof-of-domain' flag files etc), they need to be added to the build folder first.


## Using an alternative deployment driver

As noted above, you can configure the deployment script to import packages containing alternative deployment drivers by listing the modules to import (comma-seperated) in the `WORDPRESS_CD_DRIVERS` environment variable.

```bash
pip install wordpress-cd-rancher
export WPCD_DRIVERS=wordpress_cd_rancher
export WPCD_PLATFORM=rancher

export WORDPRESS_BEANSTALK_APP_ID=foo
export WORDPRESS_BEANSTALK_ENV_ID=bar
#...other platform-specific variables/creds...
deploy-wp-site -v
```

NOTE: the above package is a fictional example. I might implement it one day.


## Integration with CI/CD systems

### GitLab

The deployment script can detect that it is being run in GitLab by the existence of [environment variables]() beginning with `CI_`.

An example `.gitlab-ci.yml` for a site repository stored on GitLab might look like this:

```yaml
stages:
  - build
  - test
  - deploy

image: registry.gitlab.com/your-organisation/wordpress-cd

before_script:
  - aws s3 sync s3://your-gitlab-ci-bucket/ssh /root/.ssh && chmod 400 /root/.ssh/id_rsa
```

The above example assumes you're using the `rsync` driver, so the S3 sync command ensures that the latest SSH public/private keys are available to without having to distribute those keys in the repo.


### Example workflow for a plugin

The `.gitlab-ci.yml` file might continue like this:

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

This tells Gitlab to use the `build-wp-plugin` script to package up the code, which will create a ZIP file in the build folder, and to store this ZIP file as an artifact for later reference.

The following environment variables can be used to adjust the build behaviour.

Env var | Description | Example value
--------|-------------|--------------
WPCD_ARTEFACT_DIR | Which subfolder of the source directory to create and use for build artefacts | `wpcd-artefacts`

[TODO] There should then be one or more 'test' stages, which will trigger third-party integration, regression, unit test and UI/UX pipelines and process their success/failure responses accordingly.

Once built and tested, the ZIP can then be deployed. The `deploy-wp-plugin` script derives the target of the deployment from the stage name. The format is roughly:

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

The beginning, build and test stages are exactly the same as for plugins, as described above, but using the `build-wp-site` script instead of the `build-wp-plugin` script, and collecting the whole build folder as an artifact, instead of just the ZIP file. For example:

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

This works by reading a `config.yml` file from the repo, and using the details provided to fetch a specific version of WordPress plus various public and private artifacts specified and assemble them into the build folder to form a full 'document root' snapshot. A sample `config.yml` file might look like this:

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

The deploy stages also work in a similar way to plugins, as described above, but instead of using replacing just the plugin (or theme) on the target host, it uses `rsync` to sync the latest build into place, ignoring only dynamic areas of the site (i.e. the `wp-config.php` file, the `wp-content/uploads` folder etc).

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

Create a `staging-env` file, containing the following...

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

Replace `theme` with `plugin` as necessary in the following examples.

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

The build stage checks for the presence of `package.json` file and runs `npm install` if found.

It also checks for a `gulpfile.js`, and runs `gulp` if found. This presumes a default gulp target has been specified.


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
