"""Extension QGIS lyrx2qlr : conversion ArcGIS Pro (.lyrx) ↔ QGIS, avec le même cœur que l'application web."""


def classFactory(iface):  # noqa: N802 (nom imposé par QGIS)
    from .plugin import Lyrx2QlrPlugin
    return Lyrx2QlrPlugin(iface)
