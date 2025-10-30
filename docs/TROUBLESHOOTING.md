# NetSentinel Troubleshooting Guide

## Table of Contents
1. [Quick Diagnosis](#quick-diagnosis)
2. [Common Issues](#common-issues)
3. [Backend Issues](#backend-issues)
4. [Frontend Issues](#frontend-issues)
5. [Integration Issues](#integration-issues)
6. [Performance Issues](#performance-issues)
7. [Getting Help](#getting-help)

---

## Quick Diagnosis

### Health Check Script

```bash
#!/bin/bash
# Quick health check for all services

echo "=== NetSentinel Health Check ==="

# Check Docker services
echo -n "Docker services: "
docker-compose ps | grep -q "Up" && echo "✅ Running" || echo "❌ Not running"

# Check API
echo -n "API server: "
curl -s http://localhost:8082/health | grep -q "healthy" && echo "✅ Healthy" || echo "❌ Unhealthy"

# Check Kafka
echo -n "Kafka: "
docker exec netsentinel-kafka kafka-topics --list --bootstrap-server localhost:9092 > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Not running"

# Check Redis
echo -n "Redis: "
docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 ping > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Not running"

# Check Elasticsearch
echo -n "Elasticsearch: "
curl -s http://localhost:9200/_cluster/health | grep -q "green\|yellow" && echo "✅ Running" || echo "❌ Not running"

# Check Grafana
echo -n "Grafana: "
curl -s http://localhost:3000/api/health | grep -q "ok" && echo "✅ Running" || echo "❌ Not running"

echo "=== Health Check Complete ==="
```

---

## Common Issues

### Issue: Services Won't Start

**Symptoms**:
- Docker containers exit immediately
- Port conflicts errors
- Permission denied errors

**Solutions**:

```bash
# 1. Check Docker logs
docker-compose logs netsentinel

# 2. Check port conflicts
# Find process using port 8082
lsof -i :8082  # macOS/Linux
netstat -ano | findstr :8082  # Windows

# Kill conflicting process
kill -9 $(lsof -t -i:8082)  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# 3. Check permissions
# Ensure you have permission to manage Docker
sudo usermod -aG docker $USER  # Linux
# Log out and log back in

# 4. Rebuild containers
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# 5. Check disk space
df -h  # macOS/Linux
Get-PSDrive -PSProvider FileSystem  # Windows PowerShell
```

---

### Issue: No Events Being Processed

**Symptoms**:
- Dashboard shows no threats
- No data in Grafana
- API returns empty results

**Diagnosis**:

```bash
# Check if events are being captured
docker-compose logs -f netsentinel | grep -i "event"

# Check Kafka topics
docker exec netsentinel-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check Kafka messages
docker exec netsentinel-kafka kafka-console-consumer --topic netsentinel-events --bootstrap-server localhost:9092 --from-beginning --max-messages 5

# Check Redis data
docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 keys "netsentinel:*"

# Test honeypot connectivity
telnet localhost 22
# Or
nc localhost 22
```

**Solutions**:

```bash
# 1. Ensure honeypot services are enabled
docker-compose exec netsentinel cat ~/.netsentinel.conf

# 2. Test honeypot manually
python -m netsentinel --dev

# 3. Check event processor logs
docker-compose logs -f event-processor

# 4. Restart services
docker-compose restart netsentinel event-processor

# 5. Generate test events
python scripts/simulate_netsentinel_event.py
```

---

### Issue: High Memory Usage

**Symptoms**:
- Containers being killed
- System slowdown
- Out of memory errors

**Diagnosis**:

```bash
# Check memory usage
docker stats netsentinel

# Check system memory
free -h  # Linux
vm_stat  # macOS
Get-ComputerInfo | Select-Object TotalPhysicalMemory  # Windows

# Check container limits
docker inspect netsentinel | grep -i memory
```

**Solutions**:

```bash
# 1. Set resource limits in docker-compose.yml
services:
  netsentinel:
    deploy:
      resources:
        limits:
          memory: 2G

# 2. Reduce event history
# In configuration file
{
  "event_history_max_size": 500,  # Reduce from 1000
  "cleanup_interval": 1800  # 30 minutes instead of 60
}

# 3. Increase system memory
# Add swap space (Linux)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 4. Restart containers
docker-compose restart
```

---

## Backend Issues

### Issue: API Not Responding

**Symptoms**:
- 500 Internal Server Error
- Connection refused
- Timeout errors

**Diagnosis**:

```bash
# Check API logs
docker-compose logs api-server

# Test API directly
curl http://localhost:8082/health

# Check if API process is running
docker-compose ps api-server

# Check configuration
docker-compose exec api-server env | grep NETSENTINEL
```

**Solutions**:

```bash
# 1. Restart API service
docker-compose restart api-server

# 2. Check Python version
docker-compose exec api-server python --version
# Should be Python 3.11+

# 3. Reinstall dependencies
docker-compose exec api-server pip install -r requirements.txt

# 4. Check for import errors
docker-compose exec api-server python -c "import netsentinel.processors.api_server"

# 5. Check port binding
docker-compose exec api-server netstat -tulpn | grep 8082
```

---

### Issue: ML Model Not Working

**Symptoms**:
- ML scores always zero
- Model training fails
- CUDA errors (if using GPU)

**Diagnosis**:

```bash
# Check ML model status
curl http://localhost:8082/ml/model-info

# Check event processor logs
docker-compose logs -f event-processor | grep -i ml

# Check if PyTorch is installed
docker-compose exec event-processor python -c "import torch; print(torch.__version__)"

# Check GPU availability (if using GPU)
docker-compose exec event-processor python -c "import torch; print(torch.cuda.is_available())"
```

**Solutions**:

```bash
# 1. Enable ML in configuration
export NETSENTINEL_ML_ENABLED=true

# 2. Install PyTorch
docker-compose exec event-processor pip install torch anomalib

# 3. For CPU-only systems, install CPU version
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Check model files
ls -la /path/to/ml-models/

# 5. Retrain model
curl -X POST http://localhost:8082/ml/train

# 6. Restart event processor
docker-compose restart event-processor
```

---

### Issue: Firewall Integration Not Working

**Symptoms**:
- IPs not being blocked
- Permission denied errors
- Firewall rules not applied

**Diagnosis**:

```bash
# Check firewall manager logs
docker-compose logs -f event-processor | grep -i firewall

# Check iptables rules
docker-compose exec event-processor iptables -L -n | grep netsentinel

# Check permissions
docker-compose exec event-processor whoami

# Test firewall command
docker-compose exec event-processor iptables -A INPUT -s 1.1.1.1 -j DROP
```

**Solutions**:

```bash
# 1. Enable privileged mode (in docker-compose.yml)
services:
  event-processor:
    privileged: true
    cap_add:
      - NET_ADMIN

# 2. Check firewall provider
# Update configuration to use available firewall
{
  "firewall": {
    "provider": "iptables"  # or "ufw", "firewalld"
  }
}

# 3. For Docker, ensure network mode is host
services:
  event-processor:
    network_mode: host

# 4. Check SELinux (Red Hat/CentOS)
getenforce  # Should be "Permissive" or "Disabled" for development

# 5. Test manual block
curl -X POST http://localhost:8082/firewall/block/1.1.1.1
```

---

## Frontend Issues

### Issue: UI Won't Load

**Symptoms**:
- Blank page
- White screen of death
- Console errors

**Diagnosis**:

```bash
# Check browser console
# Open DevTools (F12) and check Console tab

# Check network requests
# Open DevTools > Network tab

# Check if dev server is running
ps aux | grep vite  # macOS/Linux
tasklist | findstr vite  # Windows

# Check port
netstat -tulpn | grep 5173  # macOS/Linux
netstat -ano | findstr 5173  # Windows
```

**Solutions**:

```bash
# 1. Restart dev server
cd netsentinel-ui
npm run dev

# 2. Clear browser cache
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete

# 3. Hard refresh
# Chrome/Firefox: Ctrl+Shift+R or Ctrl+F5

# 4. Check Node.js version
node --version  # Should be 18+

# 5. Reinstall dependencies
cd netsentinel-ui
rm -rf node_modules package-lock.json
npm install

# 6. Clear Vite cache
rm -rf node_modules/.vite
npm run dev
```

---

### Issue: Mock Data Not Loading

**Symptoms**:
- Empty tables
- No metrics displayed
- Loading spinner never stops

**Diagnosis**:

```bash
# Check mock service
cd netsentinel-ui/src
cat services/threats-service.ts

# Check mock data
cat mock/threats-mock.ts

# Check network requests in browser DevTools
# Should see mock API calls
```

**Solutions**:

```bash
# 1. Check service import
# In your component
import { getThreats } from '@/services/threats-service';

# 2. Verify mock data format
# Ensure mock data matches expected type
npm run check  # Type checking

# 3. Check for errors in console
# Look for TypeScript or runtime errors

# 4. Test mock service directly
cd netsentinel-ui
node -e "const service = require('./src/services/threats-service.ts'); console.log(service.getThreats())"

# 5. Check Service Worker (if enabled)
# Disable service worker in DevTools > Application > Service Workers
```

---

### Issue: Build Fails

**Symptoms**:
- npm run build fails
- TypeScript errors
- Module not found errors

**Diagnosis**:

```bash
# Check TypeScript errors
cd netsentinel-ui
npm run check

# Check for missing dependencies
npm list

# Check build logs
npm run build 2>&1 | tee build.log
```

**Solutions**:

```bash
# 1. Fix TypeScript errors
npm run check

# 2. Install missing dependencies
npm install <missing-package>

# 3. Update all dependencies
npm update

# 4. Check Node.js version
node --version  # Should be 18+
npm --version   # Should be 9+

# 5. Clear caches and rebuild
rm -rf node_modules package-lock.json .vite dist
npm install
npm run build

# 6. Check for circular dependencies
npx madge --circular src/

# 7. Increase Node memory
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

---

## Integration Issues

### Issue: Kafka Connection Failed

**Symptoms**:
- Events not being sent to Kafka
- Connection refused errors
- Timeout errors

**Diagnosis**:

```bash
# Check Kafka logs
docker-compose logs -f kafka

# Check Kafka connectivity
docker exec netsentinel-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check environment variables
docker-compose exec netsentinel env | grep KAFKA

# Test from host
telnet localhost 9092
```

**Solutions**:

```bash
# 1. Check Kafka is healthy
docker-compose ps kafka

# 2. Restart Kafka
docker-compose restart kafka

# 3. Check ZooKeeper
docker-compose ps zookeeper

# 4. Update Kafka settings
# In docker-compose.yml
services:
  kafka:
    environment:
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092

# 5. Check network configuration
docker network ls
docker network inspect netsentinel_default

# 6. Verify Kafka topic exists
docker exec netsentinel-kafka kafka-topics --create --topic netsentinel-events --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

---

### Issue: Redis Connection Failed

**Symptoms**:
- Threat data not persisting
- Cache misses
- Connection errors

**Diagnosis**:

```bash
# Check Redis logs
docker-compose logs -f redis

# Test Redis connection
docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 ping

# Check Redis data
docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 keys "*"

# Check memory usage
docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 info memory
```

**Solutions**:

```bash
# 1. Check Redis is running
docker-compose ps redis

# 2. Restart Redis
docker-compose restart redis

# 3. Check password configuration
# Ensure NETSENTINEL_REDIS_PASSWORD matches in all services

# 4. Clear Redis data
docker exec netsentinel-redis redis-cli -a hybrid-detection-2024 FLUSHDB

# 5. Increase Redis memory
# In docker-compose.yml
services:
  redis:
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

---

### Issue: Database Connection Issues

**Symptoms**:
- Elasticsearch/InfluxDB not accessible
- Query failures
- Timeout errors

**Diagnosis**:

```bash
# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check InfluxDB
curl http://localhost:8086/health

# Check service logs
docker-compose logs -f elasticsearch
docker-compose logs -f influxdb

# Check disk space
docker exec netsentinel-elasticsearch df -h
docker exec netsentinel-influxdb df -h
```

**Solutions**:

```bash
# 1. Restart database services
docker-compose restart elasticsearch influxdb

# 2. Check memory settings
# In docker-compose.yml
services:
  elasticsearch:
    environment:
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"

# 3. Free up disk space
docker system prune -a

# 4. Check permissions
docker exec netsentinel-elasticsearch ls -la /usr/share/elasticsearch/data

# 5. For InfluxDB, check initialization
docker-compose exec influxdb influx bucket list
```

---

## Performance Issues

### Issue: Slow API Responses

**Symptoms**:
- API requests take > 1 second
- Timeout errors
- Database query timeouts

**Diagnosis**:

```bash
# Check API metrics
curl http://localhost:8082/metrics | grep response_time

# Check resource usage
docker stats netsentinel

# Profile API requests
# Add timing logs in code
import time
start = time.time()
# ... API code ...
end = time.time()
print(f"Request took {end - start}s")
```

**Solutions**:

```bash
# 1. Increase API resources
# In docker-compose.yml
services:
  api-server:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

# 2. Enable caching
# In configuration
{
  "cache": {
    "enabled": true,
    "ttl": 300
  }
}

# 3. Optimize database queries
# Add indexes
# Use connection pooling

# 4. Scale horizontally
# For Kubernetes
kubectl scale deployment netsentinel-api --replicas=3

# 5. Profile and optimize hot paths
# Use profiling tools
```

---

## Getting Help

### Self-Help Resources

1. **Documentation**: Check `docs/` directory
2. **API Docs**: http://localhost:8082/docs
3. **Logs**: Check container logs
4. **Health Checks**: Run health check script

### Community Support

1. **GitHub Issues**: [Report issues](https://github.com/your-org/netsentinel/issues)
2. **GitHub Discussions**: [Ask questions](https://github.com/your-org/netsentinel/discussions)
3. **Stack Overflow**: Tag questions with `netsentinel`

### Collecting Debug Information

When reporting issues, include:

```bash
# System information
uname -a
docker --version
docker-compose --version
python --version
node --version

# Service status
docker-compose ps

# Recent logs
docker-compose logs --tail=100 netsentinel > logs.txt

# Health check output
./health-check.sh > health.txt

# Configuration (sanitized)
docker-compose config > config.txt
```

### Report Template

```markdown
**Issue Description**:
[Brief description]

**Steps to Reproduce**:
1. Step 1
2. Step 2
3. ...

**Expected Behavior**:
[What should happen]

**Actual Behavior**:
[What actually happens]

**Environment**:
- OS: [OS version]
- Docker: [Version]
- Python: [Version]
- Node: [Version]

**Logs**:
[Attach relevant logs]

**Additional Context**:
[Any other relevant information]
```

---

**Remember**: Most issues can be resolved by checking logs and restarting services!

**Last Updated**: January 2024  
**Version**: 1.0.0

