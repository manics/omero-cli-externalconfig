#!/usr/bin/env python

import logging
import os
from omero.cli import BaseControl
from . import update_from_environment, update_from_multilevel_dictfile


DEFAULT_LOGLEVEL = logging.WARNING


def _omerodir(ctx):
    omerodir = os.getenv("OMERODIR")
    if not omerodir or not os.path.isdir(omerodir):
        ctx.die(100, "OMERODIR not set")
    return omerodir


class ExternalConfigControl(BaseControl):
    def _configure(self, parser):
        parser.set_defaults(func=self.todo)
        parser.add_argument(
            "--verbose",
            "-v",
            action="count",
            default=0,
            help="Increase verbosity (can be used multiple times)",
        )

    def todo(self, args):
        loglevel = max(DEFAULT_LOGLEVEL - 10 * args.verbose, 10)
        logging.getLogger("omero_externalconfig").setLevel(level=loglevel)
        omerodir = _omerodir(self.ctx)
        update_from_environment(omerodir)
        update_from_multilevel_dictfile(omerodir, "todo")
        # self.ctx.out(m)
