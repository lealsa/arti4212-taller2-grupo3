@echo off
REM Pruebas automaticas. Requiere correr_windows.bat antes. Registro: pruebas_log.txt
setlocal
cd /d "%~dp0"
REM El entorno va fuera de la carpeta del repositorio: Drive u OneDrive intentarian subir sus ~40.000 archivos.
if not defined PETROANDES_VENV set PETROANDES_VENV=%LOCALAPPDATA%\petroandes-venv
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set LOG=%~dp0pruebas_log.txt
echo === inicio %date% %time% === > "%LOG%"
if not exist "%PETROANDES_VENV%\Scripts\activate.bat" (echo ERROR: no existe el entorno en %PETROANDES_VENV% (lo crea correr_windows.bat) >> "%LOG%" & goto fallo)
call "%PETROANDES_VENV%\Scripts\activate.bat"
python -c "import pytest" 2>nul || python -m pip install -e ".[st,laya,dev]" >> "%LOG%" 2>&1
python -m pytest -q >> "%LOG%" 2>&1 || goto fallo
echo === OK %date% %time% === >> "%LOG%"
goto fin
:fallo
echo === FALLO (codigo %errorlevel%) %date% %time% === >> "%LOG%"
:fin
endlocal
