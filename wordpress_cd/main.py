#!/usr/bin/env python

import os
import os.path
import sys
import time
import argparse

import logging
_logger = logging.getLogger(__name__)

def usage():
    print("Usage:")
    print("  build-wp-site [-v] [-d]  Build site artifacts using 'config.xml' in current directory.")
    print("  build-wp-plugin [-v] [-d]  Build plugin found in current directory.")
    print("  build-wp-theme [-v] [-d]  Build theme found in current directory.")
    print("  test-wp-site [-v] [-d]  TODO: Run tests using artifacts from build directory.")
    print("  test-wp-plugin [-v] [-d]  TODO: Run tests on plugin found in current directory.")
    print("  test-wp-theme [-v] [-d]  TODO: Run tests on theme found in current directory.")
    print("  deploy-wp-site [-v] [-d]  Deploy site artifacts to site specified via environment variables.")
    print("  deploy-wp-plugin [-v] [-d]  Deploy plugin to site specified via environment variables..")
    print("  deploy-wp-theme [-v] [-d]  Deploy theme to site specified via environment variables.")
    print("Arguments:")
    print("  -v  Be mildly verbose while running.")
    print("  -d  Include debugging output.")


def main():
    # Determine what mode we're running in based on the command line wrapper
    # that was invoked
    command_run = os.path.basename(sys.argv[0])

    # Read common command line arguments
    parser = argparse.ArgumentParser()
    #parser.add_argument('configfile', metavar='configfile', nargs=1,
    #           help='name of configuration file to use for this run')
    parser.add_argument('-v', dest='verbose', action='store_true')
    parser.add_argument('-d', dest='debug', action='store_true')
    args = parser.parse_args()
    #configfile = args.configfile[0]

    # Enable logging if verbosity requested
    log_level = logging.WARNING
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=log_level,
        datefmt='%Y-%m-%d %H:%M:%S')

    # Act according to command run
    if command_run[0:6] == 'build-':
        import wordpress_cd.build
        if command_run == 'build-wp-plugin':
            return wordpress_cd.build.build_plugin(args)
        elif command_run == 'build-wp-theme':
            return wordpress_cd.build.build_theme(args)
        elif command_run == 'build-wp-site':
            return wordpress_cd.build.build_site(args)
    elif command_run[0:5] == 'test-':
        import wordpress_cd.test
        if command_run == 'test-wp-plugin':
            return wordpress_cd.test.test_plugin(args)
        elif command_run == 'test-wp-theme':
            return wordpress_cd.test.test_theme(args)
        elif command_run == 'test-wp-site':
            return wordpress_cd.test.test_site(args)
    elif command_run[0:7] == 'deploy-':
        import wordpress_cd.deploy
        if command_run == 'deploy-wp-plugin':
            return wordpress_cd.deploy.deploy_plugin(args)
        elif command_run == 'deploy-wp-theme':
            return wordpress_cd.deploy.deploy_theme(args)
        elif command_run == 'deploy-wp-site':
            return wordpress_cd.deploy.deploy_site(args)

    return usage()

if __name__ == '__main__':
    sys.exit(main())
