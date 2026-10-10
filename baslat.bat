@echo off
rem 30A Studio: gerekirse kurar, sonra programi konsol penceresi olmadan baslatir.
rem "baslat.bat kur" kurulumu zorla yapar; program kurulum damgasi tutmazsa bunu kendisi cagirir.
rem Bu dosya yalnizca ASCII metin icerir ve CRLF satir sonlariyla kaydedilir (sistem kod sayfasi 936).
setlocal
set "ROOT=%~dp0"
rem Konsolun kod sayfasi cikista eski haline dondurulur ("baslat.bat kur" acik bir konsolda da calistirilabilir).
for /f "tokens=2 delims=:." %%a in ('chcp') do set "OLDCP=%%a"
chcp 65001 >nul
title 30A Studio
cd /d "%ROOT%"

set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "VENV_PYW=%ROOT%.venv\Scripts\pythonw.exe"
set "STAMP=%ROOT%.venv\studio-kurulum.txt"
set "PYTHON="
set "FIRST_INSTALL="
set "PYTHONUTF8=1"

if /i "%~1"=="kur" goto install
if not exist "%VENV_PYW%" goto install
"%VENV_PY%" -m studio.install_stamp check >nul 2>nul
if %errorlevel% neq 0 goto install
goto launch

:install
echo Kurulum basliyor (ilk seferde birkac dakika surebilir)...
if not exist "%STAMP%" set "FIRST_INSTALL=1"
rem Sanal ortamin Python'u calismiyorsa ya da 3.12'den eskiyse ortam yeniden kurulur.
"%VENV_PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if %errorlevel% neq 0 goto create_venv
if exist "%VENV_PYW%" goto packages

:create_venv
call :find_python
if not defined PYTHON goto no_python
echo Sanal ortam hazirlaniyor...
%PYTHON% -m venv --clear "%ROOT%.venv"
if %errorlevel% neq 0 goto venv_failed

:packages
echo Paketler kuruluyor...
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements-lock.txt
if %errorlevel% neq 0 goto pip_failed
"%VENV_PY%" -m studio.install_stamp write
if %errorlevel% neq 0 goto stamp_failed
echo Kurulum tamamlandi.
if defined FIRST_INSTALL call :shortcut

:launch
rem Masaustu kisayoluyla ayni komut: "-X utf8" Python'u UTF-8 kipinde calistirir.
start "" "%VENV_PYW%" -X utf8 -m studio
if not defined FIRST_INSTALL goto done
echo Program aciliyor. Bu pencere birkac saniye sonra kendiliginden kapanacak.
timeout /t 8 >nul 2>nul

:done
if defined OLDCP chcp %OLDCP% >nul 2>nul
exit /b 0

rem Python 3.12 veya daha yenisini sirayla "py -3.12", "py -3" ve "python" ile arar; bulursa PYTHON'a yazar.
:find_python
for %%C in ("py -3.12" "py -3" "python") do if not defined PYTHON call :try_python %%~C
exit /b 0

:try_python
%* -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if %errorlevel% equ 0 set "PYTHON=%*"
exit /b 0

:shortcut
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%kisayol-olustur.ps1"
if %errorlevel% neq 0 goto shortcut_failed
echo Bundan sonra programi masaustundeki "30A Studio" simgesiyle acabilirsiniz.
exit /b 0

:shortcut_failed
echo Masaustu kisayolu olusturulamadi. Programi bu dosyaya cift tiklayarak da acabilirsiniz.
exit /b 0

:no_python
echo.
echo Python 3.12 veya daha yeni bir surum bulunamadi.
echo Python'u https://www.python.org/downloads/ adresinden indirip kurun,
echo sonra bu dosyaya tekrar cift tiklayin.
goto fail

:venv_failed
echo.
echo Sanal ortam olusturulamadi. Bu pencerenin ekran goruntusunu alip yardim isteyin.
goto fail

:pip_failed
echo.
echo Paket kurulumu basarisiz oldu. Internet baglantinizi kontrol edip bu dosyaya tekrar cift tiklayin.
goto fail

:stamp_failed
echo.
echo Kurulum bilgisi kaydedilemedi. Bu pencerenin ekran goruntusunu alip yardim isteyin.
goto fail

:fail
pause
if defined OLDCP chcp %OLDCP% >nul 2>nul
exit /b 1
