import type { HoneypotServiceType } from '@/types';
import { faker } from '@faker-js/faker';

/**
 * Generate dynamic mock honeypot services
 */
export const generateMockHoneypots = (count: number = 8): HoneypotServiceType[] => {
  const serviceTemplates = [
    { name: "SSH Honeypot", port: 22, protocol: "TCP" },
    { name: "FTP Honeypot", port: 21, protocol: "TCP" },
    { name: "Telnet Honeypot", port: 23, protocol: "TCP" },
    { name: "SMTP Honeypot", port: 25, protocol: "TCP" },
    { name: "HTTP Honeypot", port: 80, protocol: "TCP" },
    { name: "HTTPS Honeypot", port: 443, protocol: "TCP" },
    { name: "POP3 Honeypot", port: 110, protocol: "TCP" },
    { name: "IMAP Honeypot", port: 143, protocol: "TCP" },
    { name: "MySQL Honeypot", port: 3306, protocol: "TCP" },
    { name: "PostgreSQL Honeypot", port: 5432, protocol: "TCP" },
    { name: "Redis Honeypot", port: 6379, protocol: "TCP" },
    { name: "MongoDB Honeypot", port: 27017, protocol: "TCP" }
  ];

  return Array.from({ length: Math.min(count, serviceTemplates.length) }, (_, index) => {
    const template = serviceTemplates[index];
    const isActive = Math.random() > 0.15; // 85% chance of being active
    const connectionCount = isActive ?
      faker.number.int({ min: 10, max: 500 }) :
      faker.number.int({ min: 0, max: 50 });

    const createdAt = new Date(Date.now() - Math.random() * 180 * 24 * 60 * 60 * 1000); // Within last 6 months
    const lastConnectionAt = isActive ?
      new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000) : // Within last week if active
      new Date(createdAt.getTime() + Math.random() * 30 * 24 * 60 * 60 * 1000); // Within first month if inactive

    return {
      id: index + 1,
      name: template.name,
      port: template.port,
      protocol: template.protocol,
      is_active: isActive ? 1 : 0,
      connection_count: connectionCount,
      last_connection_at: lastConnectionAt.toISOString(),
      created_at: createdAt.toISOString(),
      updated_at: lastConnectionAt.toISOString()
    };
  });
};

/**
 * Mock honeypot service data - dynamically generated
 */
export const mockHoneypots: HoneypotServiceType[] = generateMockHoneypots(10);

/**
 * Generate honeypots by protocol
 */
export const generateHoneypotsByProtocol = (protocol: 'TCP' | 'UDP', count: number = 4): HoneypotServiceType[] => {
  return Array.from({ length: count }, (_, index) => {
    const port = protocol === 'TCP' ?
      faker.helpers.arrayElement([22, 21, 23, 25, 80, 443, 3306, 5432]) :
      faker.helpers.arrayElement([53, 67, 68, 161, 162, 514]);

    const isActive = Math.random() > 0.2; // 80% chance of being active
    const connectionCount = isActive ? faker.number.int({ min: 5, max: 200 }) : faker.number.int({ min: 0, max: 20 });

    return {
      id: Date.now() + index,
      name: `${protocol} Service on Port ${port}`,
      port,
      protocol,
      is_active: isActive ? 1 : 0,
      connection_count: connectionCount,
      last_connection_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
      created_at: new Date(Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date().toISOString()
    };
  });
};

/**
 * Generate active honeypots only
 */
export const generateActiveHoneypots = (count: number = 6): HoneypotServiceType[] => {
  return Array.from({ length: count }, (_, index) => {
    const honeypot = generateMockHoneypots(1)[0];
    return {
      ...honeypot,
      id: Date.now() + index,
      is_active: 1,
      connection_count: faker.number.int({ min: 20, max: 300 }),
      last_connection_at: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(), // Within last 24 hours
    };
  });
};

/**
 * Get honeypot statistics
 */
export const getHoneypotStats = () => {
  const active = mockHoneypots.filter(h => h.is_active === 1);
  const totalConnections = mockHoneypots.reduce((sum, h) => sum + h.connection_count, 0);
  const avgConnections = Math.round(totalConnections / mockHoneypots.length);

  return {
    total: mockHoneypots.length,
    active: active.length,
    inactive: mockHoneypots.length - active.length,
    totalConnections,
    avgConnections,
    protocols: [...new Set(mockHoneypots.map(h => h.protocol))],
    lastActivity: new Date(Math.max(...mockHoneypots.map(h => h.last_connection_at ? new Date(h.last_connection_at).getTime() : 0))).toISOString()
  };
};
