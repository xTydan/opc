@echo off
setlocal
cd /d "%~dp0"

set "INPUT=%~1"
if not defined INPUT (
  echo OLX PC Flipping Scanner
  echo.
  set /p "INPUT=Podaj pelna sciezke do pliku CSV lub JSON: "
)

if not exist "%INPUT%" (
  echo.
  echo Nie znaleziono pliku: "%INPUT%"
  pause
  exit /b 1
)

if not exist "reports" mkdir "reports"

echo.
echo Analizuje plik: "%INPUT%"
py -3 "scripts\analyze_import.py" "%INPUT%" --output "reports\report.json"
if errorlevel 1 (
  echo.
  echo Analiza zakonczona bledem. Sprawdz komunikat powyzej.
  pause
  exit /b 1
)

echo.
echo Otwieram panel...
start "" "%CD%\docs\index.html"
echo.
echo Raport zapisano w reports\report.json
pause
