import type { NetworkDeviceType, NetworkConnectionType, NetworkTopology } from '@/types';

/**
 * Mock network devices
 */
export const mockNetworkDevices: NetworkDeviceType[] = [
  {
    id: 1,
    hostname: "server-01",
    ip_address: "192.168.1.10",
    device_type: "Server",
    os_info: "Ubuntu 22.04 LTS",
    mac_address: "00:11:22:33:44:55",
    vendor: "Dell",
    location: "Data Center A",
    is_online: 1,
    last_seen_at: "2025-10-27T10:30:00Z",
    vulnerability_score: 25,
    created_at: "2025-01-15T08:00:00Z",
    updated_at: "2025-10-27T10:30:00Z"
  },
  {
    id: 2,
    hostname: "workstation-01",
    ip_address: "192.168.1.20",
    device_type: "Workstation",
    os_info: "Windows 11 Pro",
    mac_address: "AA:BB:CC:DD:EE:FF",
    vendor: "HP",
    location: "Office Floor 1",
    is_online: 1,
    last_seen_at: "2025-10-27T10:25:00Z",
    vulnerability_score: 15,
    created_at: "2025-02-20T09:00:00Z",
    updated_at: "2025-10-27T10:25:00Z"
  },
  {
    id: 3,
    hostname: "router-main",
    ip_address: "192.168.1.1",
    device_type: "Router",
    os_info: "Cisco IOS 15.4",
    mac_address: "11:22:33:44:55:66",
    vendor: "Cisco",
    location: "Network Core",
    is_online: 1,
    last_seen_at: "2025-10-27T10:35:00Z",
    vulnerability_score: 45,
    created_at: "2024-12-01T10:00:00Z",
    updated_at: "2025-10-27T10:35:00Z"
  }
];

/**
 * Mock network connections
 */
export const mockNetworkConnections: NetworkConnectionType[] = [
  {
    id: 1,
    source_device_id: 2,
    destination_device_id: 1,
    source_port: 54321,
    destination_port: 80,
    protocol: "TCP",
    connection_state: "ESTABLISHED",
    bandwidth_usage: 125000,
    packet_count: 1500,
    created_at: "2025-10-27T10:20:00Z",
    updated_at: "2025-10-27T10:30:00Z"
  },
  {
    id: 2,
    source_device_id: 1,
    destination_device_id: 3,
    source_port: 443,
    destination_port: 443,
    protocol: "TCP",
    connection_state: "ESTABLISHED",
    bandwidth_usage: 256000,
    packet_count: 3200,
    created_at: "2025-10-27T09:45:00Z",
    updated_at: "2025-10-27T10:25:00Z"
  }
];

/**
 * Mock network topology
 */
export const mockNetworkTopology: NetworkTopology = {
  devices: mockNetworkDevices,
  connections: mockNetworkConnections
};
