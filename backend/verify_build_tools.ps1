# Verify Visual Studio Build Tools Installation
# Run this script after installing Visual Studio Build Tools

Write-Host "Checking for Visual Studio Build Tools..." -ForegroundColor Cyan

# Check for cl.exe (C++ compiler)
$clPath = Get-Command cl.exe -ErrorAction SilentlyContinue
if ($clPath) {
    Write-Host "✓ C++ Compiler (cl.exe) found at: $($clPath.Source)" -ForegroundColor Green
    Write-Host "  Version info:" -ForegroundColor Yellow
    & cl.exe 2>&1 | Select-Object -First 3
} else {
    Write-Host "✗ C++ Compiler (cl.exe) not found in PATH" -ForegroundColor Red
    Write-Host "  Make sure you:" -ForegroundColor Yellow
    Write-Host "  1. Installed 'Desktop development with C++' workload" -ForegroundColor Yellow
    Write-Host "  2. Restarted PowerShell/terminal after installation" -ForegroundColor Yellow
    Write-Host "  3. Opened 'Developer Command Prompt for VS 2022' or run:" -ForegroundColor Yellow
    Write-Host "     `& 'C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'" -ForegroundColor Gray
}

# Check for cmake
$cmakePath = Get-Command cmake.exe -ErrorAction SilentlyContinue
if ($cmakePath) {
    Write-Host "`n✓ CMake found at: $($cmakePath.Source)" -ForegroundColor Green
    & cmake.exe --version | Select-Object -First 1
} else {
    Write-Host "`n✗ CMake not found (optional, but recommended)" -ForegroundColor Yellow
}

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. If cl.exe was found, you can now install implicit:" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Gray
Write-Host "   .venv\Scripts\activate" -ForegroundColor Gray
Write-Host "   pip install -r requirements.txt" -ForegroundColor Gray
Write-Host "`n2. If cl.exe was NOT found, try opening 'Developer Command Prompt for VS 2022'" -ForegroundColor White
Write-Host "   from Start Menu, then navigate to backend folder and retry." -ForegroundColor Gray

