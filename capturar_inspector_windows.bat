@echo off
REM Captura del MCP Inspector. Requiere el indice construido y Node.js. Registro: inspector_log.txt
setlocal
cd /d "%~dp0"
REM El entorno va fuera de la carpeta del repositorio: Drive u OneDrive intentarian subir sus ~40.000 archivos.
if not defined PETROANDES_VENV set PETROANDES_VENV=%LOCALAPPDATA%\petroandes-venv
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set LOG=%~dp0inspector_log.txt
echo === inicio %date% %time% === > "%LOG%"
call "%PETROANDES_VENV%\Scripts\activate.bat"
python herramientas\capturar_inspector.py >> "%LOG%" 2>&1 || goto fallo
echo === OK %date% %time% === >> "%LOG%"
goto fin
:fallo
echo === FALLO (codigo %errorlevel%) %date% %time% === >> "%LOG%"
:fin
endlocal
