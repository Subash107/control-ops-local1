@echo off
setlocal

echo [DevOps Control Plane] Starting...
echo Building and starting containers...
docker compose up --build -d
if errorlevel 1 (
  echo Failed to start containers. Ensure Docker Desktop is running.
  exit /b 1
)

echo Waiting for services...
timeout /t 3 >nul

echo Opening browser...
start "" "http://localhost:9000"

echo Done.
endlocal
