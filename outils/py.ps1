# Lance le Python fourni avec QGIS (avec PyQGIS), en rendant accessibles le cœur (src/)
# et les outils de développement installés dans .devdeps/ (pytest…).
# Exemples :
#   .\outils\py.ps1 -m pytest
#   .\outils\py.ps1 -m lyrx2qlr exemples\lyrx -o sorties
# Variable QGIS_RACINE : dossier d'installation de QGIS s'il n'est pas dans C:\Program Files.
$racine = Split-Path -Parent $PSScriptRoot
$qgis = $env:QGIS_RACINE
if (-not $qgis) {
    $trouve = Get-ChildItem "C:\Program Files" -Directory -Filter "QGIS 3*" -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    if (-not $trouve) { Write-Error "QGIS introuvable dans C:\Program Files. Indiquer son dossier dans la variable QGIS_RACINE."; exit 1 }
    $qgis = $trouve.FullName
}
$pyhome = Get-ChildItem "$qgis\apps" -Directory -Filter "Python3*" | Select-Object -First 1
$appli = if (Test-Path "$qgis\apps\qgis-ltr") { "$qgis\apps\qgis-ltr" } else { "$qgis\apps\qgis" }
$env:PYTHONHOME = $pyhome.FullName
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:QGIS_PREFIX_PATH = $appli -replace "\\", "/"
$env:QT_PLUGIN_PATH = "$appli\qtplugins;$qgis\apps\qt5\plugins"
$env:PATH = "$appli\bin;$qgis\bin;$qgis\apps\qt5\bin;$($pyhome.FullName)\Scripts;$env:WINDIR\system32;$env:WINDIR"
$env:PYTHONPATH = "$racine\src;$racine\.devdeps;$appli\python"
$env:GDAL_DATA = "$qgis\apps\gdal\share\gdal"
$env:PROJ_DATA = "$qgis\share\proj"
& "$qgis\bin\python.exe" @args
exit $LASTEXITCODE
