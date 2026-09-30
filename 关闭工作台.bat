@echo off
rem ===================================================================
rem  A-share web workbench stopper (Windows)
rem
rem  Stops the workbench / realtime dashboard started by the project
rem  launcher, by killing whatever listens on 127.0.0.1:38473 together
rem  with its child processes.
rem
rem  Port: defaults to 38473 (deliberately uncommon). Override by setting
rem  WORKBENCH_PORT before running, e.g.  set WORKBENCH_PORT=48000
rem
rem  NOTE 1: This file is deliberately ASCII-only. cmd.exe parses .bat
rem  content with the system ANSI codepage (CP936 on zh-CN Windows), so
rem  UTF-8 Chinese text in commands/comments gets mis-decoded and breaks
rem  parsing. The Python program prints its own (Chinese) messages.
rem
rem  NOTE 2: Control flow is intentionally FLAT (if ... goto). Nested
rem  parenthesised blocks with trailing redirections make cmd mis-parse
rem  and abort with ". was unexpected at this time".
rem
rem  NOTE 3: Only netstat + taskkill + powershell are used. wmic is gone
rem  on current Windows builds, and tasklist may be denied in restricted
rem  shells. taskkill can be refused in hardened environments, so each
rem  kill falls back to PowerShell Stop-Process. Delays use ping, NOT
rem  timeout: `timeout` aborts with "Input redirection is not supported"
rem  whenever stdio is redirected.
rem ===================================================================
setlocal enabledelayedexpansion
if not defined WORKBENCH_PORT set "WORKBENCH_PORT=38473"
set "PORT=%WORKBENCH_PORT%"
set "FOUND="

rem ---- 1) find the listener on the port ----
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    set "FOUND=1"
    echo [stopper] port %PORT% is held by PID %%P - terminating process tree ...
    taskkill /F /T /PID %%P >nul 2>nul
    if errorlevel 1 (
        echo [stopper] taskkill was refused - falling back to PowerShell ...
        powershell -NoProfile -NonInteractive -Command "Stop-Process -Id %%P -Force -ErrorAction SilentlyContinue" >nul 2>nul
    )
)

if not defined FOUND (
    echo [stopper] nothing is listening on port %PORT% - nothing to stop.
    goto :verify
)

ping -n 3 127.0.0.1 >nul 2>nul

rem ---- 2) second pass in case a child took over the port ----
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    echo [stopper] PID %%P still holds port %PORT% - forcing again ...
    taskkill /F /PID %%P >nul 2>nul
    if errorlevel 1 powershell -NoProfile -NonInteractive -Command "Stop-Process -Id %%P -Force -ErrorAction SilentlyContinue" >nul 2>nul
    ping -n 2 127.0.0.1 >nul 2>nul
)

:verify
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>nul
if errorlevel 1 (
    echo [stopper] port %PORT% is free - workbench stopped.
) else (
    echo [stopper] WARNING: port %PORT% is still held.
    echo [stopper] Close the minimized "A-share workbench" window manually.
)

endlocal
