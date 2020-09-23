#!/usr/bin/env python

# Strict type annotations without annotations on omero.* is difficult
# type: ignore

from glob import glob
import logging
import os
from omero.cli import BaseControl
from . import (
    reset_configuration,
    update_from_environment,
    update_from_multilevel_dictfile,
)


DEFAULT_LOGLEVEL = logging.WARNING


def _omerodir(ctx):
    omerodir = os.getenv("OMERODIR")
    if not omerodir or not os.path.isdir(omerodir):
        ctx.die(100, "OMERODIR not set")
    return omerodir


class ExternalConfigControl(BaseControl):
    def _configure(self, parser):
        parser.set_defaults(func=self.externalconfig)

        parser.add_argument(
            "--verbose",
            "-v",
            action="count",
            default=0,
            help="Increase verbosity (can be used multiple times)",
        )

        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing configuration",
        )

        parser.add_argument(
            "--glob",
            action="store_true",
            help="Expand file arguments using shell globbing",
        )

        parser.add_argument(
            "file", nargs="*", help="Load configuration from this file"
        )

        parser.add_argument(
            "--fromenv",
            action="store_true",
            help=(
                "Update the OMERO configuration from environment variables. "
                "These will be updated after any files are parsed."
            ),
        )

    def externalconfig(self, args):
        loglevel = max(DEFAULT_LOGLEVEL - 10 * args.verbose, 10)
        logging.getLogger("omero_externalconfig").setLevel(level=loglevel)
        omerodir = _omerodir(self.ctx)

        if args.reset:
            reset_configuration(omerodir)

        for inputf in args.file:
            if args.glob:
                files = sorted(glob(inputf))
            else:
                files = [inputf]
            for f in files:
                update_from_multilevel_dictfile(omerodir, f)

        if args.fromenv:
            update_from_environment(omerodir)
