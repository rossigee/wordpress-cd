# TODO: Test stages are still to be implemented.
#
# Ideally, a test site will be used and Amazon Device Farm will be pointed to
# that site and test suites triggered. Something like that.
#

def _test_module(args, type):
    raise NotImplementedError()

def test_plugin(args):
    _test_module(args, "plugin")

def test_theme(args):
    _test_module(args, "theme")

def test_site(args):
    raise NotImplementedError()
