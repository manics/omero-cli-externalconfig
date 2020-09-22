#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configure OMERO from external data-sources
"""

import json
import logging
import os
from re import sub
from typing import Any, Dict, List, Union
from omero.config import ConfigXml  # type: ignore
from omero.util import pydict_text_io  # type: ignore

log = logging.getLogger(__name__)

DictOrList = Union[Dict[Any, Any], List[Any]]


class ExternalConfigException(Exception):
    """
    Exception thrown when an invalid property or value is found
    """

    pass


def _get_omeroweb_default(key: str) -> DictOrList:
    """
    Based on
    https://github.com/ome/omero-py/blob/v5.8.0/src/omero/plugins/prefs.py#L368
    """
    try:
        from omeroweb import settings  # type: ignore

        setting = settings.CUSTOM_SETTINGS_MAPPINGS.get(key)
        default = setting[2](setting[1]) if setting else []
    except Exception as e:
        raise ExternalConfigException(
            "Cannot retrieve default value for property %s: %s" % (key, e)
        )
    if not isinstance(default, (dict, list)):
        raise ExternalConfigException(
            "Property %s is not a dict or list" % key
        )
    return default


def _add_or_append(
    config: ConfigXml, key: str, values: DictOrList
) -> DictOrList:
    """
    Add values (dict) or append values (list) to a property.
    Based on
    https://github.com/ome/omero-py/blob/v5.8.0/src/omero/plugins/prefs.py#L383
    """
    if key in config.keys():
        json_value = json.loads(config[key])
    elif key.startswith("omero.web."):
        json_value = _get_omeroweb_default(key)
    else:
        # Key doesn't have a value so just return input instead of trying to
        # figure out the type
        return values
    if isinstance(json_value, list) and isinstance(values, list):
        json_value.extend(values)
    elif isinstance(json_value, dict) and isinstance(values, dict):
        json_value.update(values)
    else:
        raise ExternalConfigException(
            "Invalid types: key:{} current:{} new:{}".format(
                key, json_value, values
            )
        )
    return json_value  # type: ignore


def update_from_environment(omerodir: str) -> None:
    """
    Updates OMERO config.xml from CONFIG_* environment variables.

    Variable names should replace "." with "_" and "_" with "__"
    Examples:
      omero.web.public.enabled: CONFIG_omero_web_public_enabled
      omero.web.public.url_filter: CONFIG_omero_web_public_url__filter

    :param omerodir str: OMERODIR
    """
    cfg = ConfigXml(os.path.join(omerodir, "etc", "grid", "config.xml"))
    try:
        for (k, v) in os.environ.items():
            if k.startswith("CONFIG_"):
                prop = k[7:]
                prop = sub("([^_])_([^_])", r"\1.\2", prop)
                prop = sub("__", "_", prop)
                log.info("Setting: %s=%s", prop, v)
                cfg[prop] = v
    finally:
        cfg.close()


def update_from_dict(omerodir: str, dj: Dict[str, Any]) -> None:
    """
    Updates OMERO config.xml from a dictionary.

    :param omerodir str: OMERODIR
    :param dj dict: Dictionary of configuration properties.
           Dictionary keys must be strings.
           If dictionary values are strings they will be used directly.
           All other types will be converted to a JSON string.
    """
    cfg = ConfigXml(os.path.join(omerodir, "etc", "grid", "config.xml"))
    try:
        for (k, v) in dj.items():
            if not isinstance(v, str):
                v = json.dumps(v, sort_keys=True, ensure_ascii=False)
            log.info("Setting: %s=%s", k, v)
            cfg[k] = v
    finally:
        cfg.close()


def add_from_dict(omerodir: str, dj: Dict[str, DictOrList]) -> None:
    """
    Updates OMERO config.xml from a dictionary whose values are lists or
    dicts.

    :param omerodir str: OMERODIR
    :param dj dict: Dictionary of configuration properties.
           Dictionary keys must be strings.
           Dictionary values must be lists or dicts.
           Each item in the list/dict will be added to the property.
    """
    cfg = ConfigXml(os.path.join(omerodir, "etc", "grid", "config.xml"))
    try:
        for (k, vs) in dj.items():
            jv = _add_or_append(cfg, k, vs)
            log.info("Appending: %s=%s", k, jv)
            cfg[k] = json.dumps(jv, sort_keys=True, ensure_ascii=False)
    finally:
        cfg.close()


def update_from_multilevel_dictfile(omerodir: str, dictfile: str) -> None:
    """
    Updates OMERO config.xml from a file containing keys containing
    dictionaries.

    This is intended to support YAML files containing Ansible style
    configuration variables to be parsed, but note variable interpolation is
    not performed.

    Each top-level key must contain a dictionary of key-value OMERO
    properties.
    Top-level keys are processed in alphanumeric order.

    If a top-level key ends in '_set' the keys in that dictionary key will
    have their values set.
    If a top-level key ends in '_append' the keys in that dictionary key will
    have their values appended to.
    All other keys are currently ignored, though this may change in future.

    :param omerodir str: OMERODIR
    :param dictfile str: Path to a file that can be parsed as a multi-level
           dictionary.
    """
    d = pydict_text_io.load(dictfile)
    for topk, topv in sorted(d.items()):
        if topk.endswith("_append"):
            add_from_dict(omerodir, topv)
        elif topk.endswith("_set"):
            update_from_dict(omerodir, topv)
        else:
            log.warning("Ignoring top-level key {}".format(topk))
