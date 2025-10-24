# NetSentinel Directory Reorganization

## 📁 **Directory Structure Changes**

This document outlines the reorganization of NetSentinel directories to improve structure and consolidate related components.

## 🚀 **Changes Made**

### **1. Moved to `src/` Directory**

#### **✅ Anomalib ML Library**
```
# Before
anomalib/                       # Root level

# After  
src/anomalib/                   # Moved to src/
```

#### **✅ Data Directory Consolidation**
```
# Before
data/                           # Root level
hybrid-data/                    # Separate directory

# After
src/data/                       # Consolidated into src/
├── config/                     # Configuration files
├── kafka/                      # Kafka configuration
├── opencanary/                 # Honeypot configuration
├── redis/                      # Redis configuration (replaces Valkey)
└── zookeeper/                  # Zookeeper configuration
```

### **2. Configuration Updates**

#### **✅ OpenCanary → NetSentinel Branding**
- **Device ID**: `opencanary-1` → `netsentinel-1`
- **Log Format**: `opencanaryd` → `netsentinel`
- **Log Files**: `/var/tmp/opencanary.log` → `/var/tmp/netsentinel.log`
- **Banners**: Updated to "NetSentinel AI Detection System"

#### **✅ Valkey → Redis Migration**
- **Removed**: `src/data/valkey/` directory
- **Added**: `src/data/redis/` with Redis configuration
- **Updated**: Redis handlers in OpenCanary config
- **Password**: `hybrid-detection-2024` → `netsentinel-ai-2024`
- **Channel**: `opencanary:alerts` → `netsentinel:alerts`

#### **✅ Kafka Configuration**
- **Log Directory**: `/kafka-logs` → `/netsentinel-kafka-logs`
- **Topic**: Updated to use `netsentinel-events`

## 📊 **New Directory Structure**

```
NetSentinel/
├── src/                        # ✅ Source code and data
│   ├── anomalib/              # ✅ ML library (moved from root)
│   ├── netsentinel/           # ✅ Main package
│   └── data/                  # ✅ Consolidated data directory
│       ├── config/            # ✅ Configuration files
│       ├── kafka/             # ✅ Kafka configuration
│       ├── opencanary/        # ✅ Honeypot configuration
│       ├── redis/             # ✅ Redis configuration (NEW)
│       └── zookeeper/         # ✅ Zookeeper configuration
├── tests/                     # ❌ Integration tests (unchanged)
├── docs/                      # ❌ Documentation (unchanged)
├── scripts/                   # ❌ Utility scripts (unchanged)
├── k8s/                       # ❌ Kubernetes manifests (unchanged)
└── requirements.txt           # ❌ Dependencies (unchanged)
```

## 🔧 **Configuration Changes**

### **1. OpenCanary Configuration**
```json
{
    "device.node_id": "netsentinel-1",
    "device.desc": "NetSentinel AI-Powered Detection System",
    "ftp.banner": "FTP server ready - NetSentinel AI Detection System",
    "http.banner": "Apache/2.4.41 (Ubuntu) - NetSentinel AI Detection System",
    "logger": {
        "formatters": {
            "syslog_rfc": {
                "format": "netsentinel[%(process)-5s:%(thread)d]: %(name)s %(levelname)-5s %(message)s"
            }
        },
        "handlers": {
            "file": {
                "filename": "/var/log/netsentinel/netsentinel.log"
            },
            "redis": {
                "class": "netsentinel.logger.RedisHandler",
                "password": "netsentinel-ai-2024",
                "channel": "netsentinel:alerts"
            }
        }
    }
}
```

### **2. Redis Configuration**
```conf
# NetSentinel Redis Configuration
bind 127.0.0.1
port 6379
maxmemory 256mb
maxmemory-policy allkeys-lru
notify-keyspace-events Ex
```

### **3. Kafka Configuration**
```properties
log.dirs=/netsentinel-kafka-logs
```

## 🎯 **Benefits of Reorganization**

### **1. Cleaner Structure**
- **Source Code**: All in `src/` directory
- **Data**: Consolidated in `src/data/`
- **External Dependencies**: Properly organized

### **2. Branding Consistency**
- **NetSentinel**: Consistent naming throughout
- **AI-Powered**: Updated descriptions
- **Modern**: Redis instead of Valkey

### **3. Configuration Management**
- **Centralized**: All configs in `src/data/`
- **Organized**: Clear separation of concerns
- **Maintainable**: Easy to update and manage

## 📋 **Migration Checklist**

### **✅ Completed**
- [x] Moved `anomalib/` to `src/anomalib/`
- [x] Consolidated `data/` and `hybrid-data/` into `src/data/`
- [x] Removed Valkey configuration
- [x] Added Redis configuration
- [x] Updated OpenCanary branding to NetSentinel
- [x] Updated Kafka configuration
- [x] Updated log formats and file paths

### **🔄 Next Steps**
- [ ] Update Docker Compose files for new paths
- [ ] Update Kubernetes manifests for new structure
- [ ] Test configuration changes
- [ ] Update documentation references

## 🚀 **Usage**

### **1. Development**
```bash
# All source code is now in src/
cd src/
python -c "from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector"

# Data files are in src/data/
ls src/data/
```

### **2. Configuration**
```bash
# OpenCanary configuration
cat src/data/opencanary/config/opencanary.conf

# Redis configuration  
cat src/data/redis/redis.conf

# Kafka configuration
cat src/data/kafka/server.properties
```

### **3. Docker/Kubernetes**
```yaml
# Update volume mounts to new paths
volumes:
  - ./src/data/redis:/etc/redis
  - ./src/data/kafka:/etc/kafka
  - ./src/data/opencanary:/etc/opencanary
```

## 🎉 **Summary**

The reorganization provides:

- ✅ **Cleaner Structure**: All source code and data in `src/`
- ✅ **Consolidated Data**: Single `src/data/` directory
- ✅ **Modern Stack**: Redis instead of Valkey
- ✅ **Consistent Branding**: NetSentinel throughout
- ✅ **Better Organization**: Clear separation of concerns

NetSentinel now has a **clean, organized structure** that's easier to maintain and deploy! 🚀

---

*Last Updated: December 19, 2024*
