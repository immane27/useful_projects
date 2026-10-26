@echo off
rem Start the app on http://localhost:8010 (Windows). Set SSH_KEY_FILE in .env to a Windows path.
cd /d "%~dp0.."
for /f "tokens=1,* delims==" %%a in ('findstr /b "SSH_KEY_FILE=" .env') do set KEY=%%b
if not exist "%KEY%" (echo SSH_KEY_FILE in .env not found: %KEY% & exit /b 1)
docker build -t file-processing-check .
docker rm -f file-processing-check >nul 2>&1
docker run -d --restart unless-stopped --name file-processing-check -p 8010:8000 --env-file .env -v "%KEY%":/keys/id:ro file-processing-check
echo Running at http://localhost:8010
