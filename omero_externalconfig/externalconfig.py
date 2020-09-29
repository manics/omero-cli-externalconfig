#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configure OMERO from external data-sources
"""

import json
import logging
import os
from re import sub
from typing import Any, Dict, List, Optional, Union
from omero.config import ConfigXml  # type: ignore
from omero.util import pydict_text_io  # type: ignore

log = logging.getLogger("omero_externalconfig")

JSONDict = Dict[str, Any]
DictOrList = Union[Dict[Any, Any], List[Any]]


class ExternalConfigException(Exception):
    """
    Exception thrown when an invalid property or value is found
    """

    pass


def _get_config_xml(omerodir: str) -> ConfigXml:
    return ConfigXml(os.path.join(omerodir, "etc", "grid", "config.xml"))


def _get_omeroweb_default(key: str) -> Optional[DictOrList]:
    """
    Based on
    https://github.com/ome/omero-py/blob/v5.8.0/src/omero/plugins/prefs.py#L368
    """
    try:
        from omeroweb import settings  # type: ignore

        setting = settings.CUSTOM_SETTINGS_MAPPINGS.get(key)
        if not setting:
            return None
        default = setting[2](setting[1])
    except Exception as e:
        raise ExternalConfigException(
            "Cannot retrieve default value for property %s: %s" % (key, e)
        )
    if not isinstance(default, (dict, list)):
        raise ExternalConfigException(
            "Property {} is not a dict or list: {}".format(key, default)
        )
    return default


def _get_current_as_json(config: ConfigXml, key: str) -> Optional[DictOrList]:
    """
    Get current key value converted from JSON to a list or dict,
    taking into account OMERO.web's defaults
    """
    if key in config.keys():
        current = json.loads(config[key])
        if not isinstance(current, (dict, list)):
            raise ExternalConfigException(
                "Property {} is not a dict or list: {}".format(key, current)
            )
        return current
    if key.startswith("omero.web."):
        return _get_omeroweb_default(key)
    return None


def _add_to_dict(config: ConfigXml, key: str, values: JSONDict) -> JSONDict:
    """
    Add values to a dict
    """
    current = _get_current_as_json(config, key)
    if current is None:
        # Key doesn't have a value so just return input instead of trying to
        # figure out the type
        return values
    if isinstance(current, dict):
        current.update(values)
        return current
    raise ExternalConfigException(
        "Expected dict for key:{} current:{}".format(key, current)
    )


def _append_to_list(config: ConfigXml, key: str, values: List[Any]) -> List[Any]:
    """
    Append values to a list.
    Based on
    https://github.com/ome/omero-py/blob/v5.8.0/src/omero/plugins/prefs.py#L383
    """
    current = _get_current_as_json(config, key)
    if current is None:
        # Key doesn't have a value so just return input instead of trying to
        # figure out the type
        return values
    if isinstance(current, list):
        current.extend(values)
        return current
    raise ExternalConfigException(
        "Expected list for key:{} current:{}".format(key, current)
    )


def reset_configuration(omerodir: str) -> None:
    """
    Delete current OMERO config.xml properties.

    :param omerodir str: OMERODIR
    """
    cfg = _get_config_xml(omerodir)
    try:
        cfg.remove()
    finally:
        cfg.close()


def update_from_environment(omerodir: str) -> None:
    """
    Updates OMERO config.xml from CONFIG_* environment variables.

    Variable names should replace "." with "_" and "_" with "__"
    Examples:
      omero.web.public.enabled: CONFIG_omero_web_public_enabled
      omero.web.public.url_filter: CONFIG_omero_web_public_url__filter

    :param omerodir str: OMERODIR
    """
    cfg = {}
    for (k, v) in os.environ.items():
        if k.startswith("CONFIG_"):
            prop = k[7:]
            prop = sub("([^_])_([^_])", r"\1.\2", prop)
            prop = sub("__", "_", prop)
            cfg[prop] = v
    update_from_dict(omerodir, cfg)


def update_from_dict(omerodir: str, dj: Dict[str, Any]) -> None:
    """
    Updates OMERO config.xml from a dictionary.

    :param omerodir str: OMERODIR
    :param dj dict: Dictionary of configuration properties.
           Dictionary keys must be strings.
           If dictionary values are strings they will be used directly.
           All other types will be converted to a JSON string.
    """
    cfg = _get_config_xml(omerodir)
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
    cfg = _get_config_xml(omerodir)
    try:
        jv = []  # type: DictOrList
        for (k, vs) in dj.items():
            if isinstance(vs, list):
                jv = _append_to_list(cfg, k, vs)
                log.info("Appending: %s=%s", k, jv)
            elif isinstance(vs, dict):
                jv = _add_to_dict(cfg, k, vs)
                log.info("Adding: %s=%s", k, jv)
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
