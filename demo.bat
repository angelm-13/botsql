@echo off
REM Demostracion del modulo de BI: un comando, una URL.
REM
REM Instala lo necesario si falta, construye la interfaz la primera vez y
REM levanta todo en http://localhost:8500 (o el puerto de BI_PORT, si ya
REM esta definido antes de correr este script).

setlocal

if "%BI_PORT%"=="" set BI_PORT=8500

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

echo   [1/4] Dependencias de Python...
python -m pip install -q -r backend\requirements.txt
if errorlevel 1 (
    echo   [!] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

if exist "frontend\dist\index.html" (
    echo   [2/4] Interfaz ya construida.
) else (
    where npm >nul 2>nul
    if errorlevel 1 (
        echo   [2/4] Sin Node.js: se arranca solo la API, sin interfaz.
        echo         Para la interfaz, instale Node 20+ desde nodejs.org y vuelva a correr.
    ) else (
        echo   [2/4] Construyendo la interfaz ^(tarda ~1 minuto la primera vez^)...
        pushd frontend
        call npm ci --no-audit --no-fund
        call npm run build
        popd
    )
)

REM Aviso temprano si el puerto ya esta ocupado por otro programa -- en mas
REM de una maquina de prueba, Docker Desktop reenviaba ahi un contenedor de
REM OTRO proyecto, y el navegador terminaba hablando con esa otra aplicacion
REM sin ningun aviso, dando la impresion de que la demostracion fallaba.
echo   [3/4] Revisando el puerto %BI_PORT%...
netstat -ano | findstr /r /c:"LISTENING" | findstr /r /c:":%BI_PORT% " >nul 2>nul
if not errorlevel 1 (
    echo.
    echo   [!] El puerto %BI_PORT% ya esta en uso por otro programa.
    echo       No es esta demostracion la que va a fallar -- es que el
    echo       navegador terminaria hablando con lo que sea que ya esta ahi.
    echo       Revise con Docker Desktop, o corra este script con otro puerto:
    echo         set BI_PORT=8501 ^&^& demo.bat
    echo.
    pause
    exit /b 1
)

echo   [4/4] Arrancando en el puerto %BI_PORT%...
echo.
cd backend
start "" http://localhost:%BI_PORT%
python demo.py

endlocal
