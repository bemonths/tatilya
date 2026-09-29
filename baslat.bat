@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto fail
)
if not exist ".venv\studio-ready" (
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-lock.txt
  if errorlevel 1 goto fail
  type nul > ".venv\studio-ready"
)
".venv\Scripts\python.exe" -X utf8 -m studio
if errorlevel 1 goto fail
exit /b 0
:fail
echo Uygulama baslatilamadi. Yukaridaki hata bilgisini paylasabilirsiniz.
pause
exit /b 1
