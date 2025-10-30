import type { NetworkDeviceType, NetworkConnectionType, NetworkTopology } from '@/types';
import { faker } from '@faker-js/faker';

/**
 * Generate dynamic mock network devices
 */
export const generateMockNetworkDevices = (count: number = 15): NetworkDeviceType[] => {
  const deviceTypes = ['Server', 'Workstation', 'Router', 'Switch', 'Firewall', 'Load Balancer', 'Printer', 'NAS', 'UPS'];
  const vendors = ['Cisco', 'Dell', 'HP', 'Juniper', 'Palo Alto', 'Fortinet', 'NetApp', 'APC', 'Ubiquiti'];
  const locations = ['Data Center A', 'Data Center B', 'Office Floor 1', 'Office Floor 2', 'Server Room', 'Network Core', 'Branch Office'];

  return Array.from({ length: count }, (_, index) => {
    const deviceType = deviceTypes[Math.floor(Math.random() * deviceTypes.length)];
    const vendor = vendors[Math.floor(Math.random() * vendors.length)];
    const location = locations[Math.floor(Math.random() * locations.length)];
    const isOnline = Math.random() > 0.1; // 90% chance of being online

    let hostname: string;
    let osInfo: string;
    let ipAddress: string;

    switch (deviceType) {
      case 'Server':
        hostname = `server-${faker.string.alphanumeric(3).toLowerCase()}`;
        osInfo = faker.helpers.arrayElement(['Ubuntu 22.04 LTS', 'CentOS 8', 'Windows Server 2022', 'RHEL 9']);
        ipAddress = `192.168.1.${10 + index}`;
        break;
      case 'Workstation':
        hostname = `ws-${faker.person.firstName().toLowerCase()}-${faker.string.alphanumeric(2).toLowerCase()}`;
        osInfo = faker.helpers.arrayElement(['Windows 11 Pro', 'Windows 10 Pro', 'macOS 14', 'Ubuntu 22.04']);
        ipAddress = `192.168.2.${20 + index}`;
        break;
      case 'Router':
        hostname = `router-${faker.helpers.arrayElement(['main', 'edge', 'core', 'border'])}${index}`;
        osInfo = faker.helpers.arrayElement(['Cisco IOS 17.3', 'Juniper Junos 21.2', 'MikroTik RouterOS 7.8']);
        ipAddress = `192.168.1.${index + 1}`;
        break;
      case 'Switch':
        hostname = `switch-${faker.helpers.arrayElement(['access', 'dist', 'core'])}${index}`;
        osInfo = faker.helpers.arrayElement(['Cisco NX-OS 9.3', 'Arista EOS 4.27', 'Juniper EX 22.1']);
        ipAddress = `192.168.1.${100 + index}`;
        break;
      default:
        hostname = `${deviceType.toLowerCase()}-${faker.string.alphanumeric(4).toLowerCase()}`;
        osInfo = 'Unknown';
        ipAddress = `192.168.3.${50 + index}`;
    }

    const vulnerabilityScore = faker.number.int({ min: 0, max: 100 });
    const createdAt = new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000); // Within last year
    const lastSeenAt = isOnline ?
      new Date(Date.now() - Math.random() * 60 * 60 * 1000) : // Within last hour if online
      new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000); // Within last week if offline

    return {
      id: index + 1,
      hostname,
      ip_address: ipAddress,
      device_type: deviceType,
      os_info: osInfo,
      mac_address: faker.internet.mac(),
      vendor,
      location,
      is_online: isOnline ? 1 : 0,
      last_seen_at: lastSeenAt.toISOString(),
      vulnerability_score: vulnerabilityScore,
      created_at: createdAt.toISOString(),
      updated_at: lastSeenAt.toISOString()
    };
  });
};

/**
 * Generate dynamic mock network connections
 */
export const generateMockNetworkConnections = (devices: NetworkDeviceType[], count: number = 20): NetworkConnectionType[] => {
  const protocols = ['TCP', 'UDP', 'ICMP'];
  const states = ['ESTABLISHED', 'LISTENING', 'TIME_WAIT', 'CLOSE_WAIT'];

  return Array.from({ length: Math.min(count, devices.length * 2) }, (_, index) => {
    const sourceDevice = faker.helpers.arrayElement(devices);
    let destinationDevice = faker.helpers.arrayElement(devices);
    // Ensure source and destination are different
    while (destinationDevice.id === sourceDevice.id) {
      destinationDevice = faker.helpers.arrayElement(devices);
    }

    const protocol = faker.helpers.arrayElement(protocols);
    let sourcePort: number;
    let destinationPort: number;

    if (protocol === 'TCP') {
      sourcePort = faker.number.int({ min: 1024, max: 65535 });
      destinationPort = faker.helpers.arrayElement([22, 80, 443, 3306, 5432, 6379, 27017]);
    } else if (protocol === 'UDP') {
      sourcePort = faker.number.int({ min: 1024, max: 65535 });
      destinationPort = faker.helpers.arrayElement([53, 67, 68, 161, 162]);
    } else {
      sourcePort = 0;
      destinationPort = 0;
    }

    const state = protocol === 'TCP' ? faker.helpers.arrayElement(states) : 'N/A';
    const bandwidthUsage = faker.number.int({ min: 1000, max: 1000000 });
    const packetCount = faker.number.int({ min: 10, max: 10000 });

    const createdAt = new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000); // Within last 24 hours
    const updatedAt = new Date(createdAt.getTime() + Math.random() * 60 * 60 * 1000); // Up to 1 hour later

    return {
      id: index + 1,
      source_device_id: sourceDevice.id,
      destination_device_id: destinationDevice.id,
      source_port: sourcePort,
      destination_port: destinationPort,
      protocol,
      connection_state: state,
      bandwidth_usage: bandwidthUsage,
      packet_count: packetCount,
      created_at: createdAt.toISOString(),
      updated_at: updatedAt.toISOString()
    };
  });
};

/**
 * Mock network devices - dynamically generated
 */
export const mockNetworkDevices: NetworkDeviceType[] = generateMockNetworkDevices(12);

/**
 * Mock network connections - dynamically generated
 */
export const mockNetworkConnections: NetworkConnectionType[] = generateMockNetworkConnections(mockNetworkDevices, 25);

/**
 * Mock network topology
 */
export const mockNetworkTopology: NetworkTopology = {
  devices: mockNetworkDevices,
  connections: mockNetworkConnections
};

/**
 * Generate devices by type
 */
export const generateDevicesByType = (deviceType: string, count: number = 5): NetworkDeviceType[] => {
  return Array.from({ length: count }, (_, index) => {
    const device = generateMockNetworkDevices(1)[0];
    return {
      ...device,
      id: Date.now() + index,
      device_type: deviceType,
      hostname: `${deviceType.toLowerCase()}-${faker.string.alphanumeric(4).toLowerCase()}`,
    };
  });
};

/**
 * Generate online devices only
 */
export const generateOnlineDevices = (count: number = 8): NetworkDeviceType[] => {
  return Array.from({ length: count }, (_, index) => {
    const device = generateMockNetworkDevices(1)[0];
    return {
      ...device,
      id: Date.now() + index,
      is_online: 1,
      last_seen_at: new Date(Date.now() - Math.random() * 10 * 60 * 1000).toISOString(), // Within last 10 minutes
    };
  });
};

/**
 * Get network statistics
 */
export const getNetworkStats = () => {
  const onlineDevices = mockNetworkDevices.filter(d => d.is_online === 1);
  const totalBandwidth = mockNetworkConnections.reduce((sum, conn) => sum + conn.bandwidth_usage, 0);
  const avgBandwidth = Math.round(totalBandwidth / mockNetworkConnections.length);

  const deviceTypes = [...new Set(mockNetworkDevices.map(d => d.device_type))];
  const vendors = [...new Set(mockNetworkDevices.map(d => d.vendor))];

  const totalPackets = mockNetworkConnections.reduce((sum, conn) => sum + conn.packet_count, 0);
  const avgPackets = Math.round(totalPackets / mockNetworkConnections.length);

  return {
    totalDevices: mockNetworkDevices.length,
    onlineDevices: onlineDevices.length,
    offlineDevices: mockNetworkDevices.length - onlineDevices.length,
    totalConnections: mockNetworkConnections.length,
    totalBandwidth,
    avgBandwidth,
    totalPackets,
    avgPackets,
    deviceTypes,
    vendors,
    protocols: [...new Set(mockNetworkConnections.map(c => c.protocol))],
    avgVulnerabilityScore: Math.round(
      mockNetworkDevices.reduce((sum, d) => sum + d.vulnerability_score, 0) / mockNetworkDevices.length
    )
  };
};
