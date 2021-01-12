# OMERO server external configuration plugin

[![Build](https://github.com/manics/omero-cli-externalconfig/workflows/Build/badge.svg)](https://github.com/manics/omero-cli-externalconfig/actions?query=branch%3Amain)
[![Build Status](https://travis-ci.com/manics/omero-cli-externalconfig.svg?branch=main)](https://travis-ci.com/manics/omero-cli-externalconfig)

Configure OMERO using environment variables, YAML, and JSON files.

## Usage

All arguments are optional

    omero externalconfig --reset --glob --fromenv file...

- `--reset`: Clear the existing configuration before loading the new configuration
- `--glob`: Expand `file` argument(s) as shell globs
- `--fromenv`: Read OMERO configuration from environment variables.
- `file...`: Zero or more YAML or JSON files can be passed.

If `--fromenv` and `file...` arguments are passed the configuration files will be loaded first, so environment variables take precedence.

## Environment variables

Read OMERO configuration from `CONFIG_*` environment variables.

Variable names should replace `.` with `_` and `_` with `__`.
Examples:

- `omero.web.public.enabled`: `CONFIG_omero_web_public_enabled`
- `omero.web.public.url_filter`: `CONFIG_omero_web_public_url__filter`

## Configuration files

Configuration files must be in either YAML or JSON format.
They should contain one or more top-level keys with names ending in `*_set` for properties to be set and `*_append` for properties to be updated by appending/adding the new values.
The values of each item in an `*_append` dictionary must be a list or dict depending on the expected type.

For example:

```yaml
server_set:
  omero.db.poolsize: 25
  omero.client.icetransports: ssl,tcp,wss

other_set:
  omero.data.dir: /data/OMERO

web_append:
  omero.web.server_list:
    # This should be appended to the default localhost
    - [omero.example.org, 4064, omero]
    - [other.example.org, 4064, other]
```

Top-level keys are processed in alphanumerical order, with latter keys overwriting earlier properties.
Other than for ordering the name of the key has no meaning.
You may wish to use it to separate your configuration into logical sections for ease of maintenance but it will be ignored by this plugin.

If the `jinja2` Python module is installed the configuration files can also be a Jinja2 template that renders to a YAML.
The filename must end in `.j2`.

## Developer notes

This project uses [setuptools-scm](https://pypi.org/project/setuptools-scm/).
To release a new version just create a tag.
