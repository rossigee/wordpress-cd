from wordpress_cd.drivers.base import randomword


# An abstraction for obtaining a test database or other dump file for the
# 'test' stage
class BaseDataSet(object):
    # Generate random id to distinguish this dataset on the backend
    def __init__(self):
        self.random_id = randomword(10)

        # We're going to create a transient database using these details
        self.mysql_db = "wpcd_test_{}".format(self.random_id)
        self.mysql_user = "wpcd_test_{}".format(self.random_id)
        self.mysql_pass = randomword(10)

    # Implement this to return a file/stream handle that can be read from
    # and fed into a file for upload, or directly into the target system.
    def get_test_file(self, filename):
        raise NotImplementedError()
