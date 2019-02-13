## Deployment stage

The deployment stage deploys the site, typically to a pre-existing environment.

Deployment drivers override/implement a `deploy_site` method to perform the actions of deployment.


## Deploying the site

As long as the necessary environment variables are set, it's just a case of running the site deploy script.

```bash
deploy-wp-site -v
```

This script will use the configured deployment driver to deploy the site.

The deployment driver will attempt to identify which CI system is running and use the environment variables specific to that system if found. You can also use the script outside of a CI system (i.e. locally) by providing the same environment variables, or the following CI-independent alternatives:

Env var | Description | Example value
--------|-------------|--------------
WPCD_JOB_ID | A unique id | `acmetest1`
WPCD_JOB_NAME | Typically the short string name of the project/repo being deployed | `acme-widget`
WPCD_GIT_BRANCH | Which branch this is a build of, to help determine which environment to deploy to. | `master` (or `develop`)


### Common configuration

If the site you are deploying to uses non-standard `WP_CONTENT_DIR` and `WP_PLUGIN_DIR` settings in it's `wp-config.php`, you need to also specify these as environment variables to the deploy stage for sites, plugins or themes.


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
* A `wp-salt.php` file, as this would break some sites which use a separate salt file (not personally recommended).
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
