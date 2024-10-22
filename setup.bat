@echo off
setlocal enabledelayedexpansion

echo Claude Engineer Setup Script
echo ============================

:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrative privileges.
    echo Please run it as an administrator.
    pause
    exit /b 1
)

:: Check and install Chocolatey
where choco >nul 2>&1
if %errorLevel% neq 0 (
    echo Installing Chocolatey...
    @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
) else (
    echo Chocolatey is already installed.
)

:: Check and install Git
where git >nul 2>&1
if %errorLevel% neq 0 (
    echo Installing Git...
    choco install git -y
) else (
    echo Git is already installed.
)

:: Check and install Python
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo Installing Python...
    choco install python -y
) else (
    echo Python is already installed.
)

:: Clone the Claude Engineer repository
if not exist "claude-engineer" (
    echo Cloning Claude Engineer repository...
    git clone https://github.com/doriandarko/claude-engineer.git
    cd claude-engineer
) else (
    echo Claude Engineer repository already exists.
    cd claude-engineer
)

:: Create and activate virtual environment
if not exist "code_execution_env" (
    echo Creating virtual environment...
    python -m venv code_execution_env
) else (
    echo Virtual environment already exists.
)

:: Activate virtual environment and install requirements
call code_execution_env\Scripts\activate.bat
echo Installing required packages...
pip install -r requirements.txt

:: Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file...
    echo ANTHROPIC_API_KEY=your_anthropic_api_key > .env
    echo TAVILY_API_KEY=your_tavily_api_key >> .env
    echo Please update the .env file with your actual API keys.
) else (
    echo .env file already exists.
)

echo Setup complete!
echo To start Claude Engineer, run: python main.py
echo Don't forget to update your API keys in the .env file.

pause
