@echo off
REM Demostracion del modulo de BI: un comando, una URL.
REM
REM Instala lo necesario si falta, construye la interfaz la primera vez y
REM levanta todo en http://localhost:5001

setlocal
cd /d "%~dp0"

echo.
echo   === Modulo de BI -- demostracion ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo   [!] No se encontro Python. Instale Python 3.11 o superior desde python.org
    echo       y marque "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo   [1/3] Dependencias de Python...
python -m pip install -q -r backend\requirements.txt
if errorlevel 1 (
    echo   [!] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

if exist "frontend\dist\index.html" (
    echo   [2/3] Interfaz ya construida.
) else (
    where npm >nul 2>nul
    if errorlevel 1 (
        echo   [2/3] Sin Node.js: se arranca solo la API, sin interfaz.
        echo         Para la interfaz, instale Node 20+ desde nodejs.org y vuelva a correr.
    ) else (
        echo   [2/3] Construyendo la interfaz ^(tarda ~1 minuto la primera vez^)...
        pushd frontend
        call npm ci --no-audit --no-fund
        call npm run build
        popd
    )
)

echo   [3/3] Arrancando...
echo.
cd backend
start "" http://localhost:5001
python demo.py

endlocal
