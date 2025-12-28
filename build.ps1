.\build_qt.ps1

# Check for UNITYPY_PATH environment variable, use default if not found
$unityPyPath = if ($env:UNITYPY_PATH) { $env:UNITYPY_PATH } else { ".venv\Lib\site-packages\UnityPy" }

pyinstaller `
    --onefile `
    --noconsole `
    --icon "./qtdesigner/images/icon.ico" `
    --add-data "$unityPyPath;UnityPy/" `
    --add-data "pages/ui;pages/ui/" `
    --hidden-import "fastparquet" `
    --name "Floowandereeze & Modding - Duel Links" `
    .\main.py