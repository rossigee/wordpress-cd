from .base import BaseDataSet, randomword

import boto3

import os

try:
    from urllib.parse import urlparse
except Exception:
    from urlparse import urlparse


class S3DataSet(BaseDataSet):
    def __init__(self):
        super(S3DataSet, self).__init__()

        try:
            # We fetch our dataset files from S3
            self.aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
            self.aws_secret_key = os.environ['AWS_SECRET_KEY']
            self.test_data_s3_url = os.environ['TEST_DATASET_S3_URL']

            # Parse the URL into parts needed later to pull the datasets
            urlbits = urlparse(self.test_data_s3_url)
            self.test_data_bucket = urlbits.netloc
            self.test_data_prefix = urlbits.path[1:]
        except KeyError as e:
            raise Exception("Missing '{0}' environment variable.".format(e))

    def get_test_file(self, filename):
        s3 = boto3.client('s3')
        s3_uri = "{}/{}".format(self.test_data_prefix, filename)
        s3_bucket = self.test_data_bucket
        response = s3.get_object(Bucket=s3_bucket, Key=s3_uri)
        return response['Body']
