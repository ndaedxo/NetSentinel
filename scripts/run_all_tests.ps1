#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run all NetSentinel test suites in recommended order

.DESCRIPTION
    Comprehensive testing workflow that runs all test scripts in the optimal sequence:
    1. Infrastructure tests
    2. Functionality tests
    3. Component-specific tests
    4. Integration tests

.PARAMETER SkipComponentTests
    Skip component-specific tests (faster execution)

.PARAMETER Quick
    Run only infrastructure and basic functionality tests

.EXAMPLE
    .\run_all_tests.ps1
    .\run_all_tests.ps1 -SkipComponentTests
    .\run_all_tests.ps1 -Quick
#>

param(
    [switch]$SkipComponentTests,
    [switch]$Quick
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

function Write-ColoredOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Title)
    Write-ColoredOutput "`n$Title" "Yellow"
    Write-ColoredOutput ("=" * $Title.Length) "Yellow"
}

function Run-Test {
    param(
        [string]$TestName,
        [string]$Command,
        [string]$WorkingDirectory = $ProjectRoot
    )

    Write-ColoredOutput "🔍 Running $TestName..." "Cyan"

    try {
        $startTime = Get-Date

        if ($WorkingDirectory -ne $ProjectRoot) {
            Push-Location $WorkingDirectory
        }

        $result = Invoke-Expression $Command

        if ($WorkingDirectory -ne $ProjectRoot) {
            Pop-Location
        }

        $endTime = Get-Date
        $duration = [math]::Round(($endTime - $startTime).TotalSeconds, 2)

        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "✅ $TestName PASSED ($duration seconds)" "Green"
            return $true
        } else {
            Write-ColoredOutput "❌ $TestName FAILED ($duration seconds)" "Red"
            return $false
        }
    }
    catch {
        Write-ColoredOutput "❌ $TestName ERROR: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Main execution
Write-Header "NetSentinel Comprehensive Test Suite"
Write-ColoredOutput "Testing all components in recommended order..." "White"

$overallStartTime = Get-Date
$testResults = @()
$totalTests = 0
$passedTests = 0

# Phase 1: Infrastructure Tests
Write-Header "Phase 1: Infrastructure & Docker Services"
$testResults += Run-Test "Docker Infrastructure" "pwsh -File scripts/test-netsentinel-docker.ps1"
$totalTests++

# Phase 2: Core Functionality Tests
Write-Header "Phase 2: Core Functionality & APIs"
$testResults += Run-Test "Comprehensive Functionality" "pwsh -File scripts/test_functionality.ps1"
$totalTests++

# Phase 3: Component-Specific Tests (skip if requested)
if (-not $SkipComponentTests -and -not $Quick) {
    Write-Header "Phase 3: Component-Specific Tests"

    $componentTests = @(
        @{Name = "Enterprise Database"; Command = "python scripts/test_enterprise_database.py"},
        @{Name = "Firewall Management"; Command = "python scripts/test_firewall.py"},
        @{Name = "Alerting System"; Command = "python scripts/test_alerting.py"},
        @{Name = "SDN Integration"; Command = "python scripts/test_sdn_integration.py"}
    )

    foreach ($test in $componentTests) {
        $testResults += Run-Test $test.Name $test.Command
        $totalTests++
    }
}

# Phase 4: Integration Tests (skip if quick mode)
if (-not $Quick) {
    Write-Header "Phase 4: Integration & Data Flow Tests"
    $testResults += Run-Test "Complete Data Flow" "python scripts/test_complete_data_flow.py"
    $totalTests++
}

# Calculate results
$passedTests = ($testResults | Where-Object { $_ -eq $true }).Count
$failedTests = $totalTests - $passedTests

$overallEndTime = Get-Date
$overallDuration = [math]::Round(($overallEndTime - $overallStartTime).TotalSeconds, 2)

# Final Results
Write-Header "FINAL TEST RESULTS"
Write-ColoredOutput "📊 Summary:" "Cyan"
Write-ColoredOutput "   Total Tests: $totalTests" "White"
Write-ColoredOutput "   Passed: $passedTests" "Green"
Write-ColoredOutput "   Failed: $failedTests" "Red"
Write-ColoredOutput "   Success Rate: $([math]::Round(($passedTests / $totalTests) * 100, 1))%" "White"
Write-ColoredOutput "   Total Time: $overallDuration seconds" "White"

if ($passedTests -eq $totalTests) {
    Write-Header "🎉 ALL TESTS PASSED!"
    Write-ColoredOutput "NetSentinel is fully operational and ready for production!" "Green"
    exit 0
} else {
    Write-Header "❌ SOME TESTS FAILED"
    Write-ColoredOutput "Please review the failed tests above and address any issues." "Red"
    Write-ColoredOutput "Use individual test scripts for detailed debugging." "Yellow"
    exit 1
}
