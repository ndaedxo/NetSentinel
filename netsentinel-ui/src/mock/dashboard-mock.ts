import type { DashboardMetrics, SystemHealthService } from '@/types';
import { faker } from '@faker-js/faker';
import { mockThreats } from './threats-mock';

/**
 * Generate dynamic dashboard metrics based on current threat data
 */
export const generateDashboardMetrics = (): DashboardMetrics => {
  const totalEvents = mockThreats.length * faker.number.int({ min: 20, max: 80 });
  const activeThreats = mockThreats.filter(t => t.is_blocked === 0).length;
  const blockedIPs = mockThreats.filter(t => t.is_blocked === 1).length;
  const systemHealth = 95 + faker.number.float({ min: 0, max: 5 }); // 95-100%
  const responseTime = faker.number.int({ min: 20, max: 150 });
  const uptime = 99 + faker.number.float({ min: 0, max: 0.9 }); // 99-99.9%

  return {
    totalEvents,
    activeThreats,
    blockedIPs,
    systemHealth: Math.round(systemHealth * 10) / 10,
    responseTime,
    uptime: Math.round(uptime * 10) / 10
  };
};

/**
 * Mock dashboard metrics - dynamically calculated
 */
export const mockDashboardMetrics: DashboardMetrics = generateDashboardMetrics();

/**
 * Generate dynamic system health services
 */
export const generateSystemHealthServices = (count: number = 8): SystemHealthService[] => {
  const serviceTemplates = [
    { name: "Threat Detection Engine", description: 'AI-powered threat detection' },
    { name: "Network Monitor", description: 'Network traffic monitoring' },
    { name: "Alert System", description: 'Automated alert generation' },
    { name: "Database", description: 'Primary data storage' },
    { name: "API Gateway", description: 'API request routing' },
    { name: "Load Balancer", description: 'Traffic distribution' },
    { name: "Cache Layer", description: 'Data caching service' },
    { name: "Logging System", description: 'Centralized logging' },
    { name: "Metrics Collector", description: 'Performance monitoring' },
    { name: "Backup Service", description: 'Data backup and recovery' }
  ];

  const statusWeights = [0.7, 0.2, 0.1]; // 70% healthy, 20% warning, 10% critical

  return Array.from({ length: Math.min(count, serviceTemplates.length) }, (_, index) => {
    const template = serviceTemplates[index];
    const statusRandom = Math.random();
    let status: 'healthy' | 'warning' | 'critical';
    let uptime: number;
    let responseTime: number;
    let errorCount: number;

    if (statusRandom < statusWeights[0]) {
      status = 'healthy';
      uptime = 99 + faker.number.float({ min: 0, max: 0.9 });
      responseTime = faker.number.int({ min: 15, max: 80 });
      errorCount = faker.number.int({ min: 0, max: 3 });
    } else if (statusRandom < statusWeights[0] + statusWeights[1]) {
      status = 'warning';
      uptime = 95 + faker.number.float({ min: 0, max: 4 });
      responseTime = faker.number.int({ min: 80, max: 200 });
      errorCount = faker.number.int({ min: 2, max: 10 });
    } else {
      status = 'critical';
      uptime = 80 + faker.number.float({ min: 0, max: 15 });
      responseTime = status === 'critical' ? 0 : faker.number.int({ min: 200, max: 1000 });
      errorCount = faker.number.int({ min: 10, max: 50 });
    }

    return {
      id: template.name.toLowerCase().replace(/\s+/g, '-'),
      name: template.name,
      status,
      uptime: Math.round(uptime * 10) / 10,
      response_time: responseTime,
      last_checked: new Date(Date.now() - faker.number.int({ min: 0, max: 300000 })), // Within last 5 minutes
      error_count: errorCount,
      description: template.description
    };
  });
};

/**
 * Mock system health services - dynamically generated
 */
export const mockSystemHealthServices: SystemHealthService[] = generateSystemHealthServices(6);

/**
 * Mock system health response
 */
export const mockSystemHealth = {
  services: mockSystemHealthServices
};

/**
 * Generate metrics with specific characteristics
 */
export const generateMetricsWithScenario = (scenario: 'normal' | 'high-activity' | 'critical' | 'maintenance'): DashboardMetrics => {
  switch (scenario) {
    case 'high-activity':
      return {
        totalEvents: faker.number.int({ min: 2000, max: 5000 }),
        activeThreats: faker.number.int({ min: 50, max: 100 }),
        blockedIPs: faker.number.int({ min: 100, max: 200 }),
        systemHealth: faker.number.float({ min: 85, max: 95 }),
        responseTime: faker.number.int({ min: 100, max: 300 }),
        uptime: faker.number.float({ min: 95, max: 99 })
      };

    case 'critical':
      return {
        totalEvents: faker.number.int({ min: 500, max: 1500 }),
        activeThreats: faker.number.int({ min: 100, max: 200 }),
        blockedIPs: faker.number.int({ min: 20, max: 50 }),
        systemHealth: faker.number.float({ min: 60, max: 80 }),
        responseTime: faker.number.int({ min: 500, max: 2000 }),
        uptime: faker.number.float({ min: 90, max: 95 })
      };

    case 'maintenance':
      return {
        totalEvents: faker.number.int({ min: 100, max: 300 }),
        activeThreats: faker.number.int({ min: 5, max: 15 }),
        blockedIPs: faker.number.int({ min: 200, max: 300 }),
        systemHealth: faker.number.float({ min: 70, max: 85 }),
        responseTime: faker.number.int({ min: 200, max: 500 }),
        uptime: faker.number.float({ min: 85, max: 90 })
      };

    case 'normal':
    default:
      return generateDashboardMetrics();
  }
};

/**
 * Generate services with specific health status
 */
export const generateServicesByHealth = (targetHealth: 'healthy' | 'warning' | 'critical', count: number = 3): SystemHealthService[] => {
  return Array.from({ length: count }, (_, index) => {
    const baseService = generateSystemHealthServices(1)[0];
    let uptime: number;
    let responseTime: number;
    let errorCount: number;

    switch (targetHealth) {
      case 'healthy':
        uptime = 99 + faker.number.float({ min: 0, max: 0.9 });
        responseTime = faker.number.int({ min: 15, max: 50 });
        errorCount = faker.number.int({ min: 0, max: 2 });
        break;
      case 'warning':
        uptime = 95 + faker.number.float({ min: 0, max: 3 });
        responseTime = faker.number.int({ min: 80, max: 150 });
        errorCount = faker.number.int({ min: 3, max: 8 });
        break;
      case 'critical':
        uptime = 80 + faker.number.float({ min: 0, max: 10 });
        responseTime = faker.number.int({ min: 500, max: 2000 });
        errorCount = faker.number.int({ min: 15, max: 100 });
        break;
    }

    return {
      ...baseService,
      id: `${baseService.id}-${targetHealth}-${index}`,
      status: targetHealth,
      uptime: Math.round(uptime * 10) / 10,
      response_time: responseTime,
      error_count: errorCount,
      last_checked: new Date()
    };
  });
};
