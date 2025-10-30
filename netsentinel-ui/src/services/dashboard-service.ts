import type { DashboardMetrics, SystemHealthService } from '@/types';
import { mockConfig } from '@/test/__mocks__/mock-config';
import { generateSystemHealthServices } from '@/mock/dashboard-mock';

/**
 * Get dashboard metrics using dynamic mocking
 */
export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay
  await store.getGenerator('threats').delay(delayRange.min * 2, delayRange.max * 2);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('network');
  }

  // Generate dynamic dashboard metrics based on current threat data
  const threats = store.getAllThreats();
  const totalEvents = threats.length * Math.floor(Math.random() * 50 + 20);
  const activeThreats = threats.filter(t => t.is_blocked === 0).length;
  const blockedIPs = threats.filter(t => t.is_blocked === 1).length;
  const systemHealth = 95 + Math.random() * 5; // 95-100%
  const responseTime = Math.floor(Math.random() * 100 + 20);
  const uptime = 99 + Math.random() * 0.9; // 99-99.9%

  return {
    totalEvents,
    activeThreats,
    blockedIPs,
    systemHealth: Math.round(systemHealth * 10) / 10,
    responseTime,
    uptime: Math.round(uptime * 10) / 10
  };
}

/**
 * Get system health status using dynamic mocking
 */
export async function getSystemHealth(): Promise<{ services: SystemHealthService[] }> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay
  await store.getGenerator('alerts').delay(delayRange.min, delayRange.max);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('server');
  }

  // Generate dynamic system health services
  const services = generateSystemHealthServices(6);

  // If no services generated, fall back to basic mock
  if (services.length === 0) {
    return {
      services: [
        {
          id: 'threat-detection',
          name: 'Threat Detection Engine',
          status: 'healthy' as const,
          uptime: 99.5,
          response_time: 45,
          last_checked: new Date(),
          error_count: 0,
          description: 'AI-powered threat detection'
        }
      ]
    };
  }

  return {
    services: services.map(service => ({
      id: service.id,
      name: service.name,
      status: service.status,
      uptime: service.uptime,
      response_time: service.response_time,
      last_checked: service.last_checked,
      error_count: service.error_count,
      description: service.description
    }))
  };
}
