@echo off
REM Rehace la evidencia con la version actual del codigo: respaldo, ingesta, evaluacion con laya,
REM prueba de envenenamiento y captura del MCP Inspector (necesita Node.js). Registro: evidencias_log.txt
setlocal
cd /d "%~dp0"
REM El entorno va fuera de la carpeta del repositorio: Drive u OneDrive intentarian subir sus ~40.000 archivos.
if not defined PETROANDES_VENV set PETROANDES_VENV=%LOCALAPPDATA%\petroandes-venv
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PETROANDES_EMBEDDINGS=st:intfloat/multilingual-e5-small
set LOG=%~dp0evidencias_log.txt
echo === inicio %date% %time% === > "%LOG%"
if not exist "%PETROANDES_VENV%\Scripts\activate.bat" (echo ERROR: no existe el entorno en %PETROANDES_VENV% (lo crea correr_windows.bat) >> "%LOG%" & goto fallo)
call "%PETROANDES_VENV%\Scripts\activate.bat"
if not exist eval\resultados_2026-11-19 (
  echo --- respaldo de eval\resultados >> "%LOG%"
  xcopy /E /I /Y eval\resultados eval\resultados_2026-11-19 >> "%LOG%" 2>&1
)
echo --- PASO ingestar >> "%LOG%"
petroandes-docs ingestar >> "%LOG%" 2>&1 || goto fallo
echo --- PASO evaluar laya >> "%LOG%"
petroandes-docs evaluar --juez laya >> "%LOG%" 2>&1 || goto fallo
echo --- PASO envenenamiento >> "%LOG%"
petroandes-docs prueba-envenenamiento >> "%LOG%" 2>&1 || goto fallo
echo --- PASO inspector >> "%LOG%"
python herramientas\capturar_inspector.py >> "%LOG%" 2>&1 || goto fallo
echo === OK %date% %time% === >> "%LOG%"
goto fin
:fallo
echo === FALLO (codigo %errorlevel%) %date% %time% === >> "%LOG%"
:fin
endlocal
