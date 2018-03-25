# WordPress Continuous Deployment/Delivery scripts

These scripts are designed to be run by in the background by CI/CD systems that handle devops for WordPress themes, plugins and sites.

GitLab, Jenkins and other CI systems all expect us to supply our own handler scripts for the 'build', 'test' and 'deploy' stages of their pipelines. These are those handlers.

They can also be used locally, independent of any revision control or CI system. For example, I use the 'build-wp-site' script locally to quickly generate clean builds with certain plugins/themes pre-installed, and use that to kick-start a local development environments.

Initially, I'm only planning to develop, test, document and support integration of these scripts with GitLab and Jenkins. Support for other CI systems should be fairly simple to implement based on these. Patches welcome :)


## Installing the scripts

Install using the ubiquitous `pip`:

```bash
pip install wordpress-cd
```

Or, if deploying from source:

```bash
python setup.py install
```


## Building a WordPress site

First, we define a site configuration by creating a 'config.yml' file.

A sample 'config.yml' file might look like this:

```yaml
# Identifier string that can be used by deployment drivers if required.
id: clubwebsite1

# The main application zipfile to base a build on.
core:
  url: https://wordpress.org/wordpress-latest.tar.gz
  # or perhaps...
  #url: https://wordpress.org/wordpress-4.9.4.tar.gz

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

# Optional: To put a specific favicon.ico file into place
favicon:
  file: favicon.ico

```

To build a document root that contains a fresh WordPress instance with those themes and plugins installed:


```bash
build-wp-site -v
```

The resulting document root will now exist in the 'build/wordpress' folder.

To run that locally as a Docker container stack, you could use the following `docker-compose.yml` file:

```yaml
version: '3'

volumes:
    db_data:
    web_data:

networks:
  default:

services:
  db:
    #image: mysql:5.7 # ...or...
    image: mariadb:latest
    volumes:
      - db_data:/var/lib/mysql
    environment:
      MYSQL_ALLOW_EMPTY_PASSWORD: "yes"
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wordpress
      MYSQL_PASSWORD: wordpress

  cache:
    image: memcached

  wordpress:
    depends_on:
      - db
      - cache
    image: wordpress
    environment:
      DB_HOST: db:3306
      DB_NAME: wordpress
      DB_USER: wordpress
      DB_PASSWORD: wordpress
      SESSION_SAVE_HANDLER: memcached
      SESSION_SAVE_PATH: cache:11211

  sslproxy:
    depends_on:
      - wordpress
    image: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - $PWD/local/ssl:/ssl
      - $PWD/local/nginx.conf:/etc/nginx/conf.d/default.conf

```

The above creates a simple local SSL proxy container that allows you to avoid various Javascript/AJAX issues with using non-secure URLS, like 'http://localhost:8000'. For this to work, it requires a 'local' folder containing a custom SSL certificate and an nginx configuration. To generate these:

```bash
mkdir -p local/ssl
cd local/ssl
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
# ...only the 'CN' field matters, and should be the hostname
```

The 'local/nginx.conf' file should contain something like:

```nginx
server {
	listen 443 ssl default_server;
	server_name _;

	ssl_certificate /ssl/cert.pem;
	ssl_certificate_key /ssl/key.pem;

	location / {
		proxy_pass http://wordpress:80/;
		proxy_set_header Host $host;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_set_header X-Proxy-Forwarded-Proto $scheme;
		proxy_set_header X-Forwarded-Port $server_port;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
	}
}

```

Although not necessary for this exercise, I typically also use a 'docker-compose.override.yml' to mount various plugins I'm working on into the container, and to persist the database to a specific location on the host.

```yaml
version: '3'

services:
  db:
    volumes:
      - /tmp/wphost1-db:/var/lib/mysql
  wordpress:
    volumes:
      # To mount the docroot from the host instead of the static container copy
      #- $PWD/build/wordpress:/var/www/public_html
      # To mount the docroot from a restored backup
      #- $PWD/backup/public_html:/var/www/public_html
      # To use a host-based WP config, i.e. to be able to tweak options etc.
      #- $PWD/wp-config.php:/var/www/public_html/wp-config.php
      # To mount in a copy of the site's uploads/media folder
      - /tmp/wphost1-uploads:/var/www/public_html/wp-content/uploads
      # For inserting custom plugins/themes for dynamic development
      #- $PWD/plugins/acme-plugin:/var/www/public_html/wp-content/plugins/acme-plugin
      #- $PWD/themes/acme-child-theme:/var/www/public_html/wp-content/themes/acme-child-theme

```

Then `docker-compose up -d` to run up the stack. Once started, you can either start from scratch or restore a database dump to pre-populate the site.

If you've restored a database dump, you will also likely want to make a copy of the 'wp-content/uploads' folder from the server you are copying to ensure that all the media is present on your local instance. In my case, I can do this fairly simply with 'rsync':

```bash
rsync -av servername:/site/folder/wp-content/uploads /tmp/wphost1-uploads
```

At this point, you just need to add a local hosts entry.

```
127.0.0.1   www.acme.test
```

If the hostname you are using locally is not the same as the hostname from the database dump, you will also need to tweak and apply the following SQL to update it:

```sql
UPDATE wp_options SET option_value = REPLACE(option_value, 'www.acme.net', 'www.acme.test');
UPDATE wp_sitemeta SET meta_value = REPLACE(meta_value, 'www.acme.net', 'www.acme.test');
UPDATE wp_usermeta SET meta_value = REPLACE(meta_value, 'www.acme.net', 'www.acme.test');
```

If you need to set/reset a user's password:

```sql
UPDATE wp_users SET user_pass = MD5("newpassword") WHERE user_email = 'you@acme.test';
```


## Testing the site

Currently, the test scripts are mostly unimplemented. It is expected that they will also use a modular approach, much like the deployment mechanism, to allow mixing/matching of different test suites/approaches.


## Deploying the site

Once the necessary environment variables have been configured, it's just a case of running the site deploy script.

```bash
deploy-wp-site -v
```

The script needs to know a few things, defined by environment variables. Many of these variables, such as commit branch, job id etc, will be provided by the CI system that's running the script.

You will just need to ensure that the following variables are set:

Env var | Description | Example value
--------|-------------|--------------
WPCD_DRIVERS | Which python modules to import to register the necessary deployment drivers (may load multiple drivers) | `wordpress_cd.drivers.rsync`
WPCD_PLATFORM | Which driver id to use to perform the deployment | `rsync`

The above are the default environment variables used. The deploy script will attempt to identify which CI system is running and use the environment variables specific to that system if found.

Where you are running the deploy script locally, you will also need to supplement the configuration with the following environment variables, which would otherwise be supplied by the CI system.

Env var | Description | Example value
--------|-------------|--------------
WPCD_JOB_NAME | Typically the short string name of the project/repo being deployed, used to package plugins/themes | `acme-widget`
WPCD_JOB_ID | (optional) A short string/numeric serial identifier for the run of this particular CI stage | `1234`
WPCD_GIT_BRANCH | Which branch this is a build of, to help determine which environment to deploy to. | `master` (or `develop`)


### Deployment with rsync

This package comes with a simple 'rsync' based deployment driver, which is selected by default if not overridden with the 'WPCD_DRIVERS' envvar.

The environment variables a typical rsync deployment needs to refer to are:

Env var | Description | Example value
--------|-------------|--------------
SSH_HOST | Host to rsync to | www.myhost.com
SSH_PORT | (optional) SSH port to rsync to | 2222 (default: 22)
SSH_USER | Username for SSH connection | www256
SSH_PASS | (optional) Password for SSH connection | topsecret (default: None, use private key)
SSH_PATH | Remote path to deploy to | /var/www/public_html


## Using an alternative deployment driver

If you don't have rsync access to your production or staging hosts, you will probably want to use an altrenative deployment driver. There are a handful of third-party python modules that implement drivers, such as:

* [wordpress-cd-s3](https://github.com/rossigee/wordpress-cd-s3) - Builds and pushes theme/plugin zipfiles to an S3 bucket for subsequent site builds to use.
* [wordpress-cd-rancher](https://github.com/rossigee/wordpress-cd-rancher) - Builds a Docker app container with the site build, registers it and deploys it to a Rancher environment.

Or, you can write your own in-house/custom/proprietary deployment driver and use that. Feel free to file requests in the bugtracker for this project.

You can tell the deployment script to import third-party or custom packages containing alternative deployment drivers by listing the modules to import (comma-seperated) in the `WPCD_DRIVERS` environment variable. The driver that will be chosen for deployment is indicated by the `WPCD_PLATFORM` variable.

For example:

```bash
pip install wordpress-cd-rancher
export WPCD_DRIVERS=wordpress_cd_rancher
export WPCD_PLATFORM=rancher
export WPCD_DOCKER_IMAGE=registry.myorganisation.org/project/wordpress:latest
export RANCHER_URL=https://rancher.myorganisation.org
export RANCHER_ACCESS_KEY=blahblah
export RANCHER_SECRET_KEY=sshsshssh
export RANCHER_ENVIRONMENT=1a1
export RANCHER_SERVICE=1s234
deploy-wp-site -v
```


## Integration with CI/CD systems

IMPORTANT: As of this version, the following examples are currently based on a work in progress and have not been fully tested yet. More work still required here.


### GitLab

The deployment script can detect that it is being run in GitLab by the existence of [environment variables](https://docs.gitlab.com/ce/ci/variables/README.html) beginning with 'CI_'.

An example '.gitlab-ci.yml' for a site repository stored on GitLab might look like this:

```yaml
stages:
  - build
  - test
  - deploy

# Fetch an image with the CD scripts ready to run
image: rossigee/wordpress-cd

# Fetch some SSH keys to use for the rsync connection later
before_script:
  - pip install awscli && aws s3 sync s3://yourbucket/ssh /root/.ssh && chmod 400 /root/.ssh/id_rsa

# Use the CD image 'build-wp-site' script to prepare the 'build' folder as an artifact
build:
  stage: build
  only:
    - master
  tags:
    - docker
  script:
    - build-wp-site -v
  artifacts:
    paths:
    - build/

# Deploy via rsync for commits to 'master' branch
deploy:
  stage: deploy
  only:
    - master
  tags:
    - docker
  script:
    - deploy-wp-site -v
  environment:
    name: my-wordpress-site
    url: https://www.mysite.com

```

The S3 sync command ensures that the latest SSH public/private keys are available to commands being run in the CD container, without actually distributing those keys in the container image. The script uses the 'aws' command line tool, which depends on the presence of 'AWS_*' environment variables or it's own configuration file.

The same kind of thing would apply for a theme or plugin. Just replace 'site' with 'plugin' or 'theme'.


### Jenkins

The deployment script can detect that it is being run as a Jenkins pipeline by the existence of certain [environment variables](https://wiki.jenkins.io/display/JENKINS/Building+a+software+project#Buildingasoftwareproject-belowJenkinsSetEnvironmentVariables) known to be set by Jenkins.

An example 'Jenkinsfile' for a site might look like this:

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo 'Building..'
                sh 'build-wp-site -v'
                archiveArtifacts artifacts: 'build/**'
            }
        }
        stage('Test') {
            steps {
                echo 'Testing..'
                sh 'test-wp-site -v'
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying....'
                sh 'deploy-wp-site -v'
            }
        }
    }
}
```
