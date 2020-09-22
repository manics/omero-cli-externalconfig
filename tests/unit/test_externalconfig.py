import os

from omero.config import ConfigXml
from omero_externalconfig import (
    update_from_environment,
    update_from_dict,
    update_from_multilevel_dictfile,
)


def _get_config(omerodir):
    configxml = ConfigXml(os.path.join(omerodir, "etc", "grid", "config.xml"))
    try:
        cfg = configxml.as_map()
        cfg.pop("omero.config.version")
        return cfg
    finally:
        configxml.close()


class TestExternalConfig(object):
    def test_update_from_environment(self, monkeypatch, tmpdir):
        (tmpdir / "etc" / "grid").ensure(dir=True)
        omerodir = str(tmpdir)
        monkeypatch.setenv("OMERODIR", str(omerodir))

        monkeypatch.setenv("CONFIG_omero_data_dir", "/external/data")
        monkeypatch.setenv("CONFIG_omero_web_public_url__filter", "/public")
        update_from_environment(omerodir)

        cfg = _get_config(omerodir)
        assert cfg == {
            "omero.data.dir": "/external/data",
            "omero.web.public.url_filter": "/public",
        }

    def test_update_from_dict(self, monkeypatch, tmpdir):
        (tmpdir / "etc" / "grid").ensure(dir=True)
        omerodir = str(tmpdir)
        monkeypatch.setenv("OMERODIR", str(omerodir))

        d = {"a": 123, "b": "c d e", "c": [{"k": "v", "b": True}]}
        update_from_dict(omerodir, d)

        cfg = _get_config(omerodir)
        assert cfg == {
            "a": "123",
            "b": "c d e",
            "c": '[{"b": true, "k": "v"}]',
        }

    def test_update_from_multilevel_dictfile(self, monkeypatch, tmpdir):
        (tmpdir / "etc" / "grid").ensure(dir=True)
        omerodir = str(tmpdir)
        monkeypatch.setenv("OMERODIR", str(omerodir))

        content = """
omero_server_config_set:
  omero.db.poolsize: 25
  # Websockets (no wss for now to avoid dealing with certificates)
  omero.client.icetransports: ssl,tcp,ws

omero_web_apps_config_append:
  omero.web.open_with:
    - - omero_iviewer
      - omero_iviewer_index
      - script_url: omero_iviewer/openwith.js
        supported_objects:
          - image
          - dataset
          - well
        label: OMERO.iviewer
    - - omero_figure
      - new_figure
      - supported_objects:
          - images
        target: _blank
        label: OMERO.figure
  omero.web.server_list:
    # This should be appended to the default localhost
    - [idr.openmicroscopy.org, 4064, idr]

omero_web_apps_config_set:
  omero.web.mapr.config:
    - menu: "gene"
      config:
        default:
          - "Gene Symbol"
        all:
          - "Gene Symbol"
          - "Gene Identifier"
        ns:
          - "openmicroscopy.org/mapr/gene"
        label: "Gene"
        case_sensitive: True
    - menu: "genesupplementary"
      config:
        default: []
        all: []
        ns:
          - "openmicroscopy.org/mapr/gene/supplementary"
        label: "Gene supplementary"

ignored_key:
  omero.data.dir: /ignored
"""
        (tmpdir / "input.yml").write(content)

        update_from_multilevel_dictfile(omerodir, str(tmpdir / "input.yml"))

        cfg = _get_config(omerodir)
        assert cfg == {
            "omero.client.icetransports": "ssl,tcp,ws",
            "omero.db.poolsize": "25",
            "omero.web.mapr.config": (
                '[{"config": {"all": ["Gene Symbol", "Gene Identifier"], '
                '"case_sensitive": true, "default": ["Gene Symbol"], '
                '"label": "Gene", "ns": ["openmicroscopy.org/mapr/gene"]}, '
                '"menu": "gene"}, {"config": {"all": [], "default": [], '
                '"label": "Gene supplementary", "ns": '
                '["openmicroscopy.org/mapr/gene/supplementary"]}, '
                '"menu": "genesupplementary"}]'
            ),
            "omero.web.open_with": (
                '[["Image viewer", "webgateway", {"script_url": '
                '"webclient/javascript/ome.openwith_viewer.js", '
                '"supported_objects": ["image"]}], ["omero_iviewer", '
                '"omero_iviewer_index", {"label": "OMERO.iviewer", '
                '"script_url": "omero_iviewer/openwith.js", '
                '"supported_objects": ["image", "dataset", "well"]}], '
                '["omero_figure", "new_figure", {"label": "OMERO.figure", '
                '"supported_objects": ["images"], "target": "_blank"}]]'
            ),
            "omero.web.server_list": (
                '[["localhost", 4064, "omero"], '
                '["idr.openmicroscopy.org", 4064, "idr"]]'
            ),
        }
