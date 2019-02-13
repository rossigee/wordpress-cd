# Drivers

This module (`wordpress-cd`) really only provides the abstract framework and a little common implementation. It is for other modules (a.k.a. drivers) to extend and implent specific methods for specific target hosting platforms, such as Amazon Beanstalk, Kubernetes, or even just some SSH/SFTP-based host somewhere. For now, we are working on the following drivers and would be glad to hear about any that others may develop.

* `wordpress-cd-k8s`
* `wordpress-cd-rsync`

Each platform may have more than one technique/approach to spinning up a test environment. You might deploy all the services and data natively to a fresh VM, or just mount folders into a container as volumes. The CI host may or may not have direct access to a test mySQL host to upload the test data, or it might have to feed it to a remote 'mysql' command via SSH. For this reason, it is expected that an organisation will develop their own driver package which either extends `wordpress_cd` and implements all the methods from scratch, or extend from one of the 'generic' platform packages and leverage some of the existing code/techniques.

Thus, an example inheritence chain would look like:

 * BaseDriver (from this package `wordpress_cd`)
 * K8SDriver (from third-party `wordpress_k8s` package)
 * AcmeWidgetsRancherDriver (a custom/proprietary package, which will contain organisation-specific extensions/overrides to the common workflows)

For example, the organisation-specific methods might override the setup and teardown methods for the DNS to use an internal nameserver for test hosts. Or include additional files in the `.ebextensions` folder of a Beanstalk application deployment.


## Platform drivers

There will be different drivers for different hosting platforms and techniques, which will be maintained seperately as python packages that depend on this one.

A driver will be a subclass of `BaseDriver` that implements the main stages involved in testing a WordPress site:

* `setup` - Running up a VM or virtualhost using the latest build, connecting it to a database containing a fresh snapshot of test data, adding a DNS entry for external access, applying an SSL certificate etc. and generally making a cleanroom instance available at a particular URL.
* `run_tests` - Invokes one or more internal or external profiling/testing tools against the newly created URL, gathering metrics/statistics/results for later presentation, including an overall pass/failure status.
* `teardown` - Revoking any generated temporary SSL certificates (if necessary), removing DNS entry, purging test database and releasing any other resources used by the test host.

There are a few environment variables this package expects to be set at runtime for the test stage to run:

Env var | Meaning | Default
--------|---------|--------
WPCD_DRIVERS | Which driver packages to load (comma-seperated if multiple) | wordpress_cd
WPCD_PLATFORM
WPCD_TEST_DOMAIN | The domain to use for creating test hostnames (typically related to a wildcard SSL cert on the test host/proxy) | test.yourdomain.com
WPDB_PREFIX | The table name prefix used by the test database snapshot | `wp_`

TODO: Include an example within this package.

The following are existing `wordress_cd` driver implementations that may serve as a useful reference or base for new ones:

* [wordpress_cd_s3](https://github.com/rossigee/wordpress-cd-s3)
* [wordpress_cd_rancher](https://github.com/rossigee/wordpress-cd-rancher)
