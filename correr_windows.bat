@echo off
REM Crea el entorno, instala, ingesta, evalua con laya y corre la prueba de envenenamiento. Registro: windows_log.txt
setlocal
cd /d "%~dp0"
REM El entorno va fuera de la carpeta del repositorio: Drive u OneDrive intentarian subir sus ~40.000 archivos.
if not defined PETROANDES_VENV set PETROANDES_VENV=%LOCALAPPDATA%\petroandes-venv
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PETROANDES_EMBEDDINGS=st:intfloat/multilingual-e5-small
set LOG=%~dp0windows_log.txt
echo === inicio %date% %time% === > "%LOG%"

set PY=
where py >nul 2>&1 && set PY=py -3
if not defined PY (where python >nul 2>&1 && set PY=python)
if not defined PY (echo ERROR: no hay Python en el PATH >> "%LOG%" & goto fin)
%PY% --version >> "%LOG%" 2>&1

if not exist "%PETROANDES_VENV%\Scripts\activate.bat" (
  echo --- creando el entorno en %PETROANDES_VENV% >> "%LOG%"
  %PY% -m venv "%PETROANDES_VENV%" >> "%LOG%" 2>&1 || goto fallo
)
call "%PETROANDES_VENV%\Scripts\activate.bat"
echo --- instalando dependencias (puede tardar varios minutos) >> "%LOG%"
python -m pip install --upgrade pip >> "%LOG%" 2>&1
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu >> "%LOG%" 2>&1
python -m pip install -e ".[st,laya,dev]" >> "%LOG%" 2>&1 || goto fallo
echo --- PASO ingestar >> "%LOG%"
petroandes-docs ingestar >> "%LOG%" 2>&1 || goto fallo
echo --- PASO evaluar laya >> "%LOG%"
petroandes-docs evaluar --juez laya >> "%LOG%" 2>&1 || goto fallo
echo --- PASO envenenamiento >> "%LOG%"
petroandes-docs prueba-envenenamiento >> "%LOG%" 2>&1 || goto fallo
echo === OK %date% %time% === >> "%LOG%"
goto fin
:fallo
echo === FALLO (codigo %errorlevel%) %date% %time% === >> "%LOG%"
:fin
echo Terminado. Registro en windows_log.txt
endlocal
