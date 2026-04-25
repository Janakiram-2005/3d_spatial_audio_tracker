@echo off
title MAT - 3D Spatial Audio Tracker
echo =======================================================
echo     MAT - MPU6050 Spatial Audio Controller
echo =======================================================
echo.

echo [1/3] Checking environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python from python.org to run this application.
    pause
    exit /b
)

echo [2/3] Connecting to the Microcontroller...
python serial_server.py

if errorlevel 1 (
    echo.
    echo Application exited with an error. 
    echo Please check the error messages above.
    pause
    exit /b
)

echo.
echo Application closed.
pause
