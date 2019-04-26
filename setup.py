from setuptools import setup

setup(name = 'wordpress-cd',
    version = '0.7.3',
    description = 'Helper scripts to assist with WordPress-related CI/CD and devops tasks (i.e. build/test/deploy workflows for use with GitLab/Jenkins etc)',
    author = 'Ross Golder',
    author_email = 'ross@golder.org',
    url = 'https://github.com/rossigee/wordpress-cd',
    packages = [
      'wordpress_cd',
      'wordpress_cd.drivers',
      'wordpress_cd.datasets',
      'wordpress_cd.notifications',
    ],
    data_files = [
      ('extras', ['extras/mu-autoloader.php'])
    ],
    entry_points = {
        'console_scripts': [
            'build-wp-site = wordpress_cd.main:main',
            'test-wp-site = wordpress_cd.main:main',
            'deploy-wp-site = wordpress_cd.main:main',
            'build-wp-plugin = wordpress_cd.main:main',
            'test-wp-plugin = wordpress_cd.main:main',
            'deploy-wp-plugin = wordpress_cd.main:main',
            'build-wp-mu-plugin = wordpress_cd.main:main',
            'test-wp-mu-plugin = wordpress_cd.main:main',
            'deploy-wp-mu-plugin = wordpress_cd.main:main',
            'build-wp-theme = wordpress_cd.main:main',
            'test-wp-theme = wordpress_cd.main:main',
            'deploy-wp-theme = wordpress_cd.main:main',
        ]
    },
    install_requires = [
        'pyyaml',
        'requests'
    ]
)
