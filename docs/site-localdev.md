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
