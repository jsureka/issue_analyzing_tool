@echo off
echo ========================================
echo INSIGHT Tool - Starting ngrok Tunnel
echo ========================================
echo.
echo Starting ngrok tunnel on port 5000...
echo Copy the forwarding URL and use it for your GitHub webhook
echo.
echo Press Ctrl+C to stop the tunnel
echo.

ngrok http 5000
