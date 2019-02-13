## Test stage

For many smaller sites and use cases, automated regression testing is not an option and you can move on to the next section regarding deployment. For some of the sites I work on, with lots of developers all making and breaking features simultaneously, automated regression testing is not really an option, it's a necessity.

To accommodate this, we abstract the key common steps that most (if not all) test and deployment workflows will need to implement for their particular target platforms. The main top-level methods we've identified for these are:

* Test stage
  * `test_site_setup` - Prepare a clean test site with fresh docroot etc, on a brand new URL, with the latest build deployed.
  * `test_site_run` - Run a set of test suites and performance/load measurement tools against the test site to determine if it works correctly and within expected parameters , and whether there are any significant performance regressions to be noted when compared to previous test runs, send notificatins/webhooks as appropriate.
  * `test_site_teardown` - Clear down and release the resources that were configured during the site setup stage.


## Testing the site

In order to 'clean room' test a site, it needs to be set up from scratch with a known set of data, and a series of tests run against the site. If all tests pass, we can proceed to the deployment stage.

As the test stage needs to orchestrate services on different hosting platform providers, it depends on external python modules (a.k.a. 'drivers') to perform the actual orchestration of hosting resources and related services.

NOTE: The same `deploy_site` method that deploys the document root to pre-configured transient test environments can also be used by the `deploy` stage to ship the build to a pre-existing production or staging environments. So the same driver is usually used by both the 'test' and 'deploy' CI stages.


## Datasets

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
