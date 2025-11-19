@echo off
echo ========================================
echo INSIGHT Tool - ngrok Configuration
echo ========================================
echo.
echo Configuring ngrok authentication token...
echo.

ngrok config add-authtoken 35bMS8l11JuYcIGeXgosv0QACrA_535j3XJ57DYJoogyweKhQ

echo.
echo ngrok configuration complete!
echo.
echo To start the ngrok tunnel, run:
echo   ngrok http 5000
echo.
echo Then in a separate terminal, start the Flask app:
echo   python main.py
echo.
pause
