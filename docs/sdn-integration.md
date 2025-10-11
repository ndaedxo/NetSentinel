# SDN Integration Guide

NetSentinel provides comprehensive Software Defined Networking (SDN) integration to enable dynamic network policy modification and automated traffic control in response to detected security threats. This allows for network-level isolation and traffic manipulation without requiring manual network device configuration.

## 🎯 Supported SDN Controllers

NetSentinel integrates with popular open-source SDN controllers:

### OpenDaylight
- **Protocol**: RESTCONF API
- **Features**: Comprehensive network topology management, flow programming
- **Use Case**: Enterprise SDN deployments with advanced features

### ONOS (Open Network Operating System)
- **Protocol**: REST API
- **Features**: Intent-based networking, distributed architecture
- **Use Case**: Carrier-grade SDN deployments

### Ryu
- **Protocol**: REST API
- **Features**: Python-based controller, research and prototyping
- **Use Case**: Development, testing, and research environments

### Floodlight
- **Protocol**: REST API
- **Features**: OpenFlow controller with web interface
- **Use Case**: Educational and small-scale deployments

## 🔧 Configuration

### Environment Variables

Configure SDN integration through environment variables:

```bash
# Enable SDN integration
SDN_ENABLED=true

# Default controller and switch settings
SDN_CONTROLLER_NAME=opendaylight
SDN_SWITCH_ID=openflow:1
SDN_QUARANTINE_DURATION=3600

# OpenDaylight Configuration
OPENDLIGHT_HOST=192.168.1.10
OPENDLIGHT_PORT=8181
OPENDLIGHT_USERNAME=admin
OPENDLIGHT_PASSWORD=admin

# ONOS Configuration
ONOS_HOST=192.168.1.11
ONOS_PORT=8181
ONOS_USERNAME=onos
ONOS_PASSWORD=rocks

# Ryu Configuration
RYU_HOST=192.168.1.12
RYU_PORT=8080
```

### Docker Compose Configuration

Add SDN environment variables to your `docker-compose.yml`:

```yaml
event-processor:
  environment:
    - SDN_ENABLED=true
    - SDN_CONTROLLER_NAME=opendaylight
    - SDN_SWITCH_ID=openflow:1
    - OPENDLIGHT_HOST=opendaylight-controller
    - OPENDLIGHT_PORT=8181
    - OPENDLIGHT_USERNAME=admin
    - OPENDLIGHT_PASSWORD=admin
```

## 📊 Network Response Actions

### Automated Quarantine

NetSentinel automatically quarantines critical threats (threat score ≥ 8.0) by:

1. **Traffic Isolation**: Blocking all traffic from malicious IPs
2. **VLAN Segregation**: Moving traffic to quarantine VLANs
3. **Time-based Policies**: Automatic policy expiration and cleanup

### Manual Control

API-driven network control for custom responses:

```bash
# Quarantine an IP manually
curl -X POST http://localhost:8082/sdn/quarantine \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.100",
    "controller": "opendaylight",
    "switch_id": "openflow:1",
    "duration": 3600,
    "quarantine_vlan": 999
  }'

# Release quarantine
curl -X DELETE http://localhost:8082/sdn/quarantine/quarantine_192.168.1.100_1234567890
```

## 🔀 Traffic Manipulation

### Traffic Redirection

Redirect suspicious traffic to monitoring or analysis systems:

```bash
curl -X POST http://localhost:8082/sdn/traffic/redirect \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.200",
    "controller": "opendaylight",
    "switch_id": "openflow:1",
    "destination_port": "2",
    "duration": 300
  }'
```

### Traffic Mirroring

Mirror traffic for passive analysis without disrupting flow:

```bash
curl -X POST http://localhost:8082/sdn/traffic/mirror \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.201",
    "controller": "opendaylight",
    "switch_id": "openflow:1",
    "mirror_port": "3",
    "duration": 300
  }'
```

## 🛡️ Quarantine Policies

### Policy Types

#### Drop-based Quarantine
- **Action**: Drop all packets from quarantined IP
- **Use Case**: Complete traffic isolation
- **Duration**: Configurable timeout

#### VLAN-based Quarantine
- **Action**: Redirect traffic to quarantine VLAN
- **Use Case**: Segregated analysis environment
- **Duration**: Time-limited access

### Policy Management

```bash
# View active quarantine policies
curl http://localhost:8082/sdn/quarantine/policies

# Response:
{
  "policies": [
    {
      "name": "quarantine_192.168.1.100_1640995200",
      "target_ip": "192.168.1.100",
      "switch_id": "openflow:1",
      "quarantine_vlan": 999,
      "duration": 3600,
      "created_at": 1640995200.123,
      "active": true
    }
  ],
  "active_count": 1
}
```

## 🚀 API Endpoints

### Status and Monitoring

```bash
# Get SDN integration status
GET /sdn/status

# Get configured controllers
GET /sdn/controllers

# Get active flows
GET /sdn/flows

# Test controller connectivity
POST /sdn/test
```

### Quarantine Management

```bash
# Create quarantine policy
POST /sdn/quarantine

# Delete quarantine policy
DELETE /sdn/quarantine/{policy_name}

# Get quarantine policies
GET /sdn/quarantine/policies
```

### Traffic Control

```bash
# Redirect traffic
POST /sdn/traffic/redirect

# Mirror traffic
POST /sdn/traffic/mirror
```

## 📈 Monitoring and Statistics

Monitor SDN integration health and performance:

```bash
curl http://localhost:8082/sdn/status
```

Response:
```json
{
  "sdn_enabled": true,
  "status": {
    "controllers": ["opendaylight"],
    "active_quarantines": 2,
    "active_flows": 5,
    "monitoring_active": true,
    "total_quarantine_policies": 15
  }
}
```

## 🛠️ Troubleshooting

### Controller Connection Issues

#### OpenDaylight Authentication

```bash
# Test authentication
curl -u admin:admin http://opendaylight:8181/restconf/operational/network-topology:network-topology

# Check if RESTCONF is enabled
curl http://opendaylight:8181/restconf/modules
```

#### ONOS Connection

```bash
# Test ONOS API
curl -u onos:rocks http://onos:8181/onos/v1/devices

# Check cluster status
curl -u onos:rocks http://onos:8181/onos/v1/cluster
```

#### Ryu Controller

```bash
# Test Ryu REST API
curl http://ryu:8080/stats/switches

# Check controller logs
docker logs ryu-controller
```

### Flow Rule Issues

#### Flow Not Applied

```bash
# Check switch connectivity
curl http://localhost:8082/sdn/test

# Verify switch ID format
# OpenDaylight: "openflow:1"
# ONOS: Device ID from /onos/v1/devices
# Ryu: Hexadecimal DPID
```

#### Flow Timeout

```bash
# Check flow expiration
curl http://localhost:8082/sdn/flows

# Monitor flow statistics
curl -u admin:admin http://opendaylight:8181/restconf/operational/opendaylight-inventory:nodes
```

### Network Issues

#### VLAN Configuration

```bash
# Verify VLAN exists on switch
# Check switch configuration for VLAN 999 (or your quarantine VLAN)

# Test VLAN connectivity
ping -I vlan999 192.168.1.1
```

#### Port Configuration

```bash
# Verify port numbers match physical switch ports
# Check OpenFlow port mapping

# Test port connectivity
ethtool eth0  # Physical interface
ip link show   # Virtual interfaces
```

## 🔒 Security Considerations

### Controller Security
- Use HTTPS for controller communication
- Implement proper authentication and authorization
- Regularly rotate controller credentials
- Restrict controller API access to trusted networks

### Network Security
- Validate all SDN commands before execution
- Implement rate limiting for API calls
- Monitor for unauthorized flow modifications
- Use secure SDN protocols (TLS, mutual authentication)

### Policy Validation
- Validate IP addresses and switch IDs
- Implement timeout limits for all policies
- Log all SDN operations for audit trails
- Implement approval workflows for critical changes

## 📊 Performance Optimization

### Flow Management
- Use appropriate flow timeouts to prevent table exhaustion
- Implement flow aggregation for similar traffic patterns
- Monitor flow table utilization
- Clean up expired flows regularly

### Controller Load Balancing
- Distribute load across multiple controller instances
- Implement connection pooling for API calls
- Cache controller responses when appropriate
- Monitor controller performance metrics

### Network Efficiency
- Minimize flow rule changes during high-traffic periods
- Use wildcard matching for efficient rule application
- Implement hierarchical flow policies
- Monitor network performance impact

## 🔄 Integration Examples

### OpenDaylight Setup

1. **Install OpenDaylight**:
   ```bash
   docker run -d -p 8181:8181 -p 6633:6633 -p 6653:6653 \
     --name opendaylight opendaylight/odl:latest
   ```

2. **Configure Features**:
   ```bash
   # Enable RESTCONF and OpenFlow
   curl -u admin:admin -X POST http://localhost:8181/restconf/config/netconf-keystore:keystore \
     -H "Content-Type: application/xml" \
     -d '<keystore xmlns="urn:ietf:params:xml:ns:yang:ietf-keystore"/>'
   ```

3. **Environment Variables**:
   ```bash
   SDN_ENABLED=true
   SDN_CONTROLLER_NAME=opendaylight
   SDN_SWITCH_ID=openflow:1
   OPENDLIGHT_HOST=opendaylight
   OPENDLIGHT_PORT=8181
   OPENDLIGHT_USERNAME=admin
   OPENDLIGHT_PASSWORD=admin
   ```

### ONOS Setup

1. **Install ONOS**:
   ```bash
   docker run -d -p 8181:8181 -p 6654:6654 \
     --name onos onosproject/onos:latest
   ```

2. **Configure Applications**:
   ```bash
   # Enable OpenFlow and REST APIs
   curl -u onos:rocks -X POST http://localhost:8181/onos/v1/applications/org.onosproject.openflow/active
   curl -u onos:rocks -X POST http://localhost:8181/onos/v1/applications/org.onosproject.rest/active
   ```

3. **Environment Variables**:
   ```bash
   SDN_ENABLED=true
   SDN_CONTROLLER_NAME=onos
   SDN_SWITCH_ID=of:0000000000000001
   ONOS_HOST=onos
   ONOS_PORT=8181
   ONOS_USERNAME=onos
   ONOS_PASSWORD=rocks
   ```

### Ryu Setup

1. **Install Ryu**:
   ```bash
   pip install ryu
   ryu-manager --wsapi-port 8080 ryu.app.simple_switch &
   ```

2. **Environment Variables**:
   ```bash
   SDN_ENABLED=true
   SDN_CONTROLLER_NAME=ryu
   SDN_SWITCH_ID=0000000000000001
   RYU_HOST=ryu-controller
   RYU_PORT=8080
   ```

## 📋 Best Practices

### Deployment Planning
- Start with test environments before production deployment
- Implement gradual rollout with feature flags
- Monitor network performance during SDN operations
- Have rollback procedures for SDN configuration changes

### Operational Monitoring
- Monitor controller health and connectivity
- Track flow rule installation success rates
- Alert on quarantine policy failures
- Log all SDN operations for compliance

### Maintenance
- Regularly review and clean up expired policies
- Update controller software and security patches
- Test SDN functionality during maintenance windows
- Document network topology and SDN configurations

---

**Integration Status**: ✅ **SDN integration fully implemented**

For additional support, check NetSentinel logs and SDN controller documentation.
