@echo off
setlocal
cd /d "%~dp0"

if not exist "download_car_images.py" (
  echo ERROR: download_car_images.py was not found.
  pause
  exit /b 1
)

echo Installing/updating required packages...
python -m pip install -r requirements-car-images.txt
if errorlevel 1 (
  echo.
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo.
echo Starting vehicle image downloader...
python download_car_images.py

echo.
echo Finished.
pause
