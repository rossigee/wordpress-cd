# Build stage for site builds

A typical, simple `build.yml` file might look like this, with a single 'build' made from a single 'layer':

```yaml
builds:
  mysite:
    core: https://wordpress.org/wordpress-latest.tar.gz
    layers:
      - common

layers:
  common:
    themes:
      - https://downloads.wordpress.org/themes/mobile.zip
    mu-plugins:
      - https://downloads.wordpress.org/plugin/wp-bcrypt.zip
    plugins:
      - https://downloads.wordpress.org/plugin/application-passwords.zip
      - https://downloads.wordpress.org/plugin/another-plugin.zip

```

This would create a build artefact that contains the above components assembled into a document root in the `build/mysite` folder.

If you're working on multiple sites, and each site needs a different set of plugins, you can list multiple builds with different sets of layers. For example:


```yaml
builds:
  sitea:
    core: https://wordpress.org/wordpress-latest.tar.gz
    layers:
      - common
      - clienta
  siteb:
    core: https://en-gb.wordpress.org/wordpress-5.0.3-en_GB.tar.gz
    layers:
      - common
      - clientb

layers:
  common:
    themes:
      - https://downloads.wordpress.org/themes/mobile.zip
      - https://downloads.wordpress.org/themes/some-parent-theme.zip
    mu-plugins:
      - https://downloads.wordpress.org/plugin/wp-bcrypt.zip
    plugins:
      - https://downloads.wordpress.org/plugin/application-passwords.zip

  clienta:
    themes:
      - https://gitlab.com/youraccount/wordpress/themes/clienta-theme/repository/master/archive.zip

  clientb:
    themes:
      - https://gitlab.com/youraccount/wordpress/themes/clientb-theme/repository/master/archive.zip
    plugins:
      - https://downloads.wordpress.org/plugin/another-plugin.zip

```


## Building a WordPress site

First, create a working directory to contain your site configuration and related files.

Within that folder, we define a `build.yml` site configuration file listing the main 'ingredients' (layers) we want our document root build(s) to consist of.

Most people will probably only want to build one site (document root), but the ability exists to create multiple different builds simultaneously.

To run the build:

```bash
build-wp-site -v
```

The resulting `build` folder will contain a folder for each build defined, and each of those will contain a `wordpress` folder with the generated document root for that build. The CI system should consider the `build` folder an artifact, as it will be expected by the subsequent testing and deployment stages.

TODO: It should probably also ZIP up the document roots, and provide the ZIP files, checksum values and perhaps the last commit message.


### URLs in the config file

The main components for the build are retrieved using `curl` as a subprocess. That means only simple 'http' or 'https' links are allowed for now.

TODO: Extend to accept `s3://` URLs for private plugin repositories hosted on the popular storage platform.

TODO: Extend to allow `envato://` (or other proprietary URL schemes) to allow the latest or specific versions of proprietary plugins or themes to be retrieved directly from their source repositories or vendor packaging system.


### Including a `wp-config.php` file

If there is a `wp-config.php` file present in the current working directory when the `build-wp-site` script is run, it is included in the build.

Typically, it's good practice to include a production-ready version of this config, but with the database settings retrieved from environment variables set by the production host.

```
define('DB_NAME', getenv("DB_NAME"));
define('DB_USER', getenv("DB_USER"));
define('DB_PASSWORD', getenv("DB_PASSWORD"));
define('DB_HOST', getenv("DB_HOST"));
```

Some people may prefer not to include a `wp-config.php` file at build time, but instead generate or include specific configs at testing and/or final deployment time.


### Including a `.htaccess` file

If there is a `.htaccess` file present in the current working directory when the `build-wp-site` script is run, it is included in the build.


### Including a `favicon.ico` file

If there is a `favicon.ico` file present in the current working directory when the `build-wp-site` script is run, it is included in the build.


## Running 'gulp'

The build stage for both sites and themes/plugins checks for the presence of `package.json` file and runs `npm install` if found.

It also checks for a `gulpfile.js`, and runs `gulp` if found. This presumes a default gulp target has been specified.
