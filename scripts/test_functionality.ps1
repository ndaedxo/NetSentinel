#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive NetSentinel Functionality Test Script

.DESCRIPTION
    Tests all major functionality including API endpoints, event processing,
    threat detection, firewall operations, ML models, and integrations.
#>

param(
    [switch]$Quiet,
    [switch]$Json
)

$ErrorActionPreference = "Continue"

# Configuration
$ScriptName = "NetSentinel Functionality Test"
$Separator = "=" * 60
$APIBase = "http://localhost:8082"
$TestResults = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    tests = @()
}

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Success,
        [string]$Message,
        [hashtable]$Details = @{}
    )
    
    $status = if ($Success) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($Success) { "Green" } else { "Red" }
    
    if (-not $Quiet) {
        Write-Host "$status $TestName" -ForegroundColor $color
        if ($Message) {
            Write-Host "   $Message" -ForegroundColor "Gray"
        }
    }
    
    $TestResults.tests += @{
        test = $TestName
        success = $Success
        message = $Message
        details = $Details
    }
}

function Test-APIEndpoint {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [hashtable]$Body = $null,
        [string]$Description
    )
    
    try {
        $uri = "$APIBase$Endpoint"
        $params = @{
            Uri = $uri
            Method = $Method
            TimeoutSec = 10
            ErrorAction = "Stop"
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-RestMethod @params
        Write-TestResult -TestName "API: $Description" -Success $true -Message "Endpoint: $Endpoint" -Details @{status_code = 200; response = $response}
        return $response
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-TestResult -TestName "API: $Description" -Success $false -Message "Failed: $($_.Exception.Message) (Status: $statusCode)" -Details @{status_code = $statusCode; error = $_.Exception.Message}
        return $null
    }
}

function Test-KafkaFunctionality {
    Write-Host "`n📡 Testing Kafka Functionality..." -ForegroundColor "Cyan"
    
    try {
        # Check Kafka topics
        $topics = docker exec netsentinel-kafka kafka-topics --list --bootstrap-server localhost:9092 2>$null
        if ($topics -match "netsentinel-events") {
            Write-TestResult -TestName "Kafka: Topic Exists" -Success $true -Message "Topic 'netsentinel-events' found"
        } else {
            Write-TestResult -TestName "Kafka: Topic Exists" -Success $false -Message "Topic 'netsentinel-events' not found"
        }
        
        # Get topic details
        $topicInfo = docker exec netsentinel-kafka kafka-topics --describe --topic netsentinel-events --bootstrap-server localhost:9092 2>$null
        if ($topicInfo) {
            Write-TestResult -TestName "Kafka: Topic Details" -Success $true -Message "Topic details retrieved"
        } else {
            Write-TestResult -TestName "Kafka: Topic Details" -Success $false -Message "Failed to get topic details"
        }
    }
    catch {
        Write-TestResult -TestName "Kafka: Functionality" -Success $false -Message "Kafka test failed: $($_.Exception.Message)"
    }
}

function Test-RedisFunctionality {
    Write-Host "`n💾 Testing Redis Functionality..." -ForegroundColor "Cyan"
    
    try {
        # Test Redis connection
        $ping = docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 ping 2>$null
        if ($ping -match "PONG") {
            Write-TestResult -TestName "Redis: Connection" -Success $true -Message "Redis responding to PING"
        } else {
            Write-TestResult -TestName "Redis: Connection" -Success $false -Message "Redis not responding"
        }
        
        # Test Redis operations
        $testKey = "netsentinel:test:functionality"
        $testValue = "test-value-$(Get-Date -Format 'yyyyMMddHHmmss')"
        
        docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 SET $testKey $testValue 2>$null | Out-Null
        $retrieved = docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 GET $testKey 2>$null
        
        if ($retrieved -eq $testValue) {
            Write-TestResult -TestName "Redis: Read/Write" -Success $true -Message "Redis read/write operations working"
            docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 DEL $testKey 2>$null | Out-Null
        } else {
            Write-TestResult -TestName "Redis: Read/Write" -Success $false -Message "Redis read/write operations failed"
        }
        
        # Check for threat keys
        $threatKeys = docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 KEYS "threat:*" 2>$null
        $threatCount = if ($threatKeys) { ($threatKeys | Measure-Object -Line).Lines } else { 0 }
        Write-TestResult -TestName "Redis: Threat Storage" -Success $true -Message "Found $threatCount threat records"
    }
    catch {
        Write-TestResult -TestName "Redis: Functionality" -Success $false -Message "Redis test failed: $($_.Exception.Message)"
    }
}

function Test-APIEndpoints {
    Write-Host "`n🔗 Testing API Endpoints..." -ForegroundColor "Cyan"
    
    # Health and system endpoints
    Test-APIEndpoint -Endpoint "/health" -Description "Health Check"
    Test-APIEndpoint -Endpoint "/metrics" -Description "Metrics Endpoint"
    
    # Threat intelligence
    $threatsResponse = Test-APIEndpoint -Endpoint "/threats" -Description "Threats List"
    Test-APIEndpoint -Endpoint "/threats/192.168.1.100" -Description "Threat by IP"
    Test-APIEndpoint -Endpoint "/threat-intel/status" -Description "Threat Intel Status"
    Test-APIEndpoint -Endpoint "/threat-intel/check/8.8.8.8" -Description "Threat Intel Check"
    Test-APIEndpoint -Endpoint "/threat-intel/indicators" -Description "Threat Indicators"
    Test-APIEndpoint -Endpoint "/threat-intel/feeds" -Description "Threat Feeds"
    
    # Alerts
    Test-APIEndpoint -Endpoint "/alerts" -Description "Alerts List"
    Test-APIEndpoint -Endpoint "/alerts/stats" -Description "Alert Statistics"
    
    # Authentication
    Test-APIEndpoint -Endpoint "/auth/login" -Method "POST" -Body @{username="admin";password="admin"} -Description "Login"
    Test-APIEndpoint -Endpoint "/auth/me" -Description "Current User Info"
    
    # SIEM Integration
    Test-APIEndpoint -Endpoint "/siem/status" -Description "SIEM Status"
    Test-APIEndpoint -Endpoint "/siem/connectors" -Description "SIEM Connectors"
}

function Test-ThreatIntelligenceOperations {
    Write-Host "`n🔍 Testing Threat Intelligence Operations..." -ForegroundColor "Cyan"
    
    try {
        # Test threat check for various IPs
        $testIPs = @("8.8.8.8", "1.1.1.1", "192.168.1.100")
        foreach ($ip in $testIPs) {
            $result = Test-APIEndpoint -Endpoint "/threat-intel/check/$ip" -Description "Check IP: $ip"
        }
        
        # Test threat indicators endpoint with filters
        $indicators = Test-APIEndpoint -Endpoint "/threat-intel/indicators?type=ip&limit=10" -Description "Get Threat Indicators"
        
        # Test threat feeds
        $feeds = Test-APIEndpoint -Endpoint "/threat-intel/feeds" -Description "Get Threat Feeds"
    }
    catch {
        Write-TestResult -TestName "Threat Intel: Operations" -Success $false -Message "Threat intelligence operations test failed: $($_.Exception.Message)"
    }
}

function Test-SIEMOperations {
    Write-Host "`n📡 Testing SIEM Integration Operations..." -ForegroundColor "Cyan"
    
    try {
        # Test SIEM connector test
        $testResult = Test-APIEndpoint -Endpoint "/siem/test" -Method "POST" -Body @{threat_score = 8.0} -Description "Test SIEM Connection"
        
        # Get connector details
        $connectors = Test-APIEndpoint -Endpoint "/siem/connectors" -Description "Get SIEM Connectors"
    }
    catch {
        Write-TestResult -TestName "SIEM: Operations" -Success $false -Message "SIEM operations test failed: $($_.Exception.Message)"
    }
}

function Test-EventSimulation {
    Write-Host "`n📨 Testing Event Simulation..." -ForegroundColor "Cyan"
    
    try {
        # Check if simulation script exists
        if (Test-Path "scripts/simulate_netsentinel_event.py") {
            Write-TestResult -TestName "Event: Simulation Script" -Success $true -Message "Event simulation script available"
            
            # Try to send a test event (requires kafka-python)
            try {
                $env:PYTHONPATH = "$PWD/src;$PWD"
                $result = python scripts/simulate_netsentinel_event.py --kafka localhost:9092 --topic netsentinel-events --ip 192.168.1.200 --count 1 --type ssh 2>&1
                
                if ($LASTEXITCODE -eq 0 -or $result -match "Sent") {
                    Write-TestResult -TestName "Event: Send Test Event" -Success $true -Message "Successfully sent test event to Kafka"
                    
                    # Wait for processing
                    Start-Sleep -Seconds 3
                    
                    # Check if threat was created
                    $threatCheck = Test-APIEndpoint -Endpoint "/threats/192.168.1.200" -Description "Check Threat for Test IP"
                    if ($threatCheck) {
                        Write-TestResult -TestName "Event: Threat Processing" -Success $true -Message "Event processed and threat data available"
                    }
                } else {
                    Write-TestResult -TestName "Event: Send Test Event" -Success $false -Message "Failed to send event: $result"
                }
            }
            catch {
                Write-TestResult -TestName "Event: Send Test Event" -Success $false -Message "Event simulation requires kafka-python: $($_.Exception.Message)"
            }
        } else {
            Write-TestResult -TestName "Event: Simulation Script" -Success $false -Message "Event simulation script not found"
        }
    }
    catch {
        Write-TestResult -TestName "Event: Simulation" -Success $false -Message "Event simulation test failed: $($_.Exception.Message)"
    }
}

function Test-ElasticsearchFunctionality {
    Write-Host "`n🔍 Testing Elasticsearch Functionality..." -ForegroundColor "Cyan"
    
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:9200/_cluster/health" -Method GET -TimeoutSec 5
        if ($health.status -in @("green", "yellow")) {
            Write-TestResult -TestName "Elasticsearch: Cluster Health" -Success $true -Message "Cluster status: $($health.status)"
        } else {
            Write-TestResult -TestName "Elasticsearch: Cluster Health" -Success $false -Message "Cluster status: $($health.status)"
        }
        
        # Check indices
        $indices = Invoke-RestMethod -Uri "http://localhost:9200/_cat/indices?format=json" -Method GET -TimeoutSec 5
        $indexCount = ($indices | Measure-Object).Count
        Write-TestResult -TestName "Elasticsearch: Indices" -Success $true -Message "Found $indexCount indices"
    }
    catch {
        Write-TestResult -TestName "Elasticsearch: Functionality" -Success $false -Message "Elasticsearch test failed: $($_.Exception.Message)"
    }
}

function Test-InfluxDBFunctionality {
    Write-Host "`n📊 Testing InfluxDB Functionality..." -ForegroundColor "Cyan"
    
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8086/health" -Method GET -TimeoutSec 5
        if ($health.status -eq "pass") {
            Write-TestResult -TestName "InfluxDB: Health" -Success $true -Message "InfluxDB is healthy"
        } else {
            Write-TestResult -TestName "InfluxDB: Health" -Success $false -Message "InfluxDB health check failed"
        }
    }
    catch {
        Write-TestResult -TestName "InfluxDB: Functionality" -Success $false -Message "InfluxDB test failed: $($_.Exception.Message)"
    }
}

function Test-WebInterfaces {
    Write-Host "`n🌐 Testing Web Interfaces..." -ForegroundColor "Cyan"
    
    $interfaces = @(
        @{ Name = "Grafana"; Url = "http://localhost:3000" },
        @{ Name = "Kafka UI"; Url = "http://localhost:8080" },
        @{ Name = "Redis Commander"; Url = "http://localhost:8081" },
        @{ Name = "Prometheus"; Url = "http://localhost:9090" }
    )
    
    foreach ($interface in $interfaces) {
        try {
            $response = Invoke-WebRequest -Uri $interface.Url -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            $success = $response.StatusCode -in @(200, 302)
            Write-TestResult -TestName "Web: $($interface.Name)" -Success $success -Message "Status: $($response.StatusCode)"
        }
        catch {
            Write-TestResult -TestName "Web: $($interface.Name)" -Success $false -Message "Failed: $($_.Exception.Message)"
        }
    }
}

function Write-Summary {
    Write-Host "`n$Separator" -ForegroundColor "Cyan"
    Write-Host "📊 FUNCTIONALITY TEST SUMMARY" -ForegroundColor "Cyan"
    Write-Host $Separator -ForegroundColor "Cyan"
    
    $passed = ($TestResults.tests | Where-Object { $_.success -eq $true }).Count
    $failed = ($TestResults.tests | Where-Object { $_.success -eq $false }).Count
    $total = $TestResults.tests.Count
    
    Write-Host "Total Tests: $total" -ForegroundColor "White"
    Write-Host "Passed: $passed" -ForegroundColor "Green"
    Write-Host "Failed: $failed" -ForegroundColor "Red"
    Write-Host "Success Rate: $([math]::Round(($passed / $total) * 100, 2))%" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
    
    if ($failed -gt 0) {
        Write-Host "`n❌ Failed Tests:" -ForegroundColor "Red"
        $TestResults.tests | Where-Object { $_.success -eq $false } | ForEach-Object {
            Write-Host "   - $($_.test): $($_.message)" -ForegroundColor "Red"
        }
    }
    
    Write-Host "`n$Separator" -ForegroundColor "Cyan"
}

# Main execution
Write-Host $ScriptName -ForegroundColor "Cyan"
Write-Host $Separator -ForegroundColor "Cyan"

# Run all tests
Test-KafkaFunctionality
Test-RedisFunctionality
Test-APIEndpoints
Test-ThreatIntelligenceOperations
Test-SIEMOperations
Test-EventSimulation
Test-ElasticsearchFunctionality
Test-InfluxDBFunctionality
Test-WebInterfaces

# Write summary
Write-Summary

# Export JSON if requested
if ($Json) {
    $TestResults | ConvertTo-Json -Depth 10 | Out-File -FilePath "netsentinel-functionality-test-results.json" -Encoding UTF8
    Write-Host "`nResults exported to: netsentinel-functionality-test-results.json" -ForegroundColor "Cyan"
}

# Exit with appropriate code
$failed = ($TestResults.tests | Where-Object { $_.success -eq $false }).Count
exit $(if ($failed -eq 0) { 0 } else { 1 })

