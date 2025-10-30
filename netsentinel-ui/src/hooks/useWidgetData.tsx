import { useMemo } from 'react';
import { mockStore } from '@/test/__mocks__/mock-generator';
import { generateSystemHealthServices } from '@/mock/dashboard-mock';
import type { ThreatType } from '@/types/threats';
import type { AlertType } from '@/types/alerts';
import type { SystemHealthData } from '@/types/dashboard';

/**
 * Hook to get threat data for widgets using dynamic mocking
 */
export function useThreatData(): ThreatType[] {
  return useMemo(() => {
    // Use the dynamic mock store to get fresh threat data
    return mockStore.getAllThreats();
  }, []);
}

/**
 * Hook to get alert data for widgets using dynamic mocking
 */
export function useAlertData(): AlertType[] {
  return useMemo(() => {
    // Get alerts from the dynamic mock store, generate if none exist
    let alerts = mockStore.get<AlertType[]>('alerts', []);
    if (alerts.length === 0) {
      const generator = mockStore.getGenerator('alerts');
      alerts = generator.generateAlerts(8);
      mockStore.set('alerts', alerts);
    }
    return alerts;
  }, []);
}

/**
 * Hook to get system health data for widgets using dynamic mocking
 */
export function useSystemHealthData(): SystemHealthData {
  return useMemo(() => {
    // Generate dynamic system health services
    const services = generateSystemHealthServices(6);

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
  }, []);
}
