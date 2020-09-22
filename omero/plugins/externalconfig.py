#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configure OMERO using external data sources
"""

import sys
from omero.cli import CLI
from omero_externalconfig.cli import ExternalConfigControl

HELP = """Configure OMERO using external data sources
"""

try:
    register("externalconfig", ExternalConfigControl, HELP)  # noqa
except NameError:
    if __name__ == "__main__":
        cli = CLI()
        cli.register("externalconfig", ExternalConfigControl, HELP)
        cli.invoke(sys.argv[1:])
