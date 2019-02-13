# WordPress Continuous Deployment/Delivery scripts

These scripts are designed to be called as part of the post-commit hook in Git repositories to facilitate custom CI/CD workflows. They are designed to be triggered by Jenkins from a `Jenkinsfile`, or from GitLab via a `.gitlab-ci.yml` file.

However, they can just as readily be used without a CI system, i.e. for creating local development environments. For example, I often use the `build-wp-site` script locally to quickly generate clean builds with certain plugins/themes pre-installed, and use that to kick-start a local development environment, using the build folder as the document root.

They were primarily aimed at building up a whole WordPress site from it's component parts, testing and deploying it. However, provisions have also been made for building themes and plugins, testing them and deploying them independently to an existing WordPress site.


# Overview

Typically, a developer or development team working on a WordPress project will need to :

* `build` a document root containing WordPress, a set of themes and plugins and various other files (config file, htaccess, favicon etc).
* `test` the built document root using a predetermined set of test data to ensure that the resulting website works as expected and no regressions have been introduced
* `deploy` the new build as a new 'version' to one or more hosts or hosting environments

The build stage is fairly simple, as it just involves downloading a bunch of resources and arranging them into a 'document root' folder. This can be achieved be defining the themes and plugins to be assembled in a simple `build.yml` file.

The test and deploy stages are slightly more complicated, as different organisations will have different workflows and techniques that they will need to apply to deploy to different testing and production platforms. Therefore functionality in the test and deploy stages is implemented using a driver-based approach so that it can be easily extended.

See the [docs](docs/) for more details.


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

These allow CI workflows for specific themes/plugins to be developed, so a particular theme/plugin can be applied to a given site without having to rebuild and redeploy the whole docroot. It also allows for fresh build of plugins and themes to be deployed as ZIP files in readiness for being included in a subsequent site build.

NOTE: The `test-*` scripts for themes and plugins are just placeholders, as it's not usually practical to do end-to-end regression testing of WP plugins, and I've not come across any plugins that have their own unit tests yet.

## Dockerisation

These scripts can be installed directly on your Jenkins (or other) CI server. However, we find it best to use a custom CI build container that contains `wordpress_cd` plus all the platform drivers we use, plus the command-line tools they depend on (such as `zip`, `mysql`, `aws`, `az`, `kubectl` etc.).

TODO: Workflow example.


## Integration with CI/CD systems

For more information see:

* [GitLab](docs/gitlab.md)
* [Jenkins](docs/jenkins.md)

Should be easy enough to adapt to other CI systems. Documentation PRs welcome.
