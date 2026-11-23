@echo off
REM Comparacion de ADR-008 con el juez laya. Requiere correr_windows.bat antes. Registro: windows_log_comparacion.txt
setlocal
cd /d "%~dp0"
REM El entorno va fuera de la carpeta del repositorio: Drive u OneDrive intentarian subir sus ~40.000 archivos.
if not defined PETROANDES_VENV set PETROANDES_VENV=%LOCALAPPDATA%\petroandes-venv
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PETROANDES_EMBEDDINGS=st:intfloat/multilingual-e5-small
set LOG=%~dp0windows_log_comparacion.txt
echo === inicio %date% %time% === > "%LOG%"
powershell -NoProfile -Command "'RAM GB: ' + [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1); 'CPU: ' + (Get-CimInstance Win32_Processor).Name" >> "%LOG%" 2>&1
call "%PETROANDES_VENV%\Scripts\activate.bat"
python -m pip install -e . >> "%LOG%" 2>&1 || goto fallo
echo --- PASO comparar >> "%LOG%"
petroandes-docs comparar --juez laya >> "%LOG%" 2>&1 || goto fallo
echo === OK %date% %time% === >> "%LOG%"
goto fin
:fallo
echo === FALLO (codigo %errorlevel%) %date% %time% === >> "%LOG%"
:fin
endlocal
