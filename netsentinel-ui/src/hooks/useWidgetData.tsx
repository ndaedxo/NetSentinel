import { useMemo } from 'react';
import { mockThreats } from '@/mock/threats-mock';
import { mockAlerts } from '@/mock/alerts-mock';
import { mockSystemHealth } from '@/mock/dashboard-mock';
import type { ThreatType } from '@/types/threats';
import type { AlertType } from '@/types/alerts';
import type { SystemHealthData } from '@/types/dashboard';

/**
 * Hook to get threat data for widgets
 */
export function useThreatData(): ThreatType[] {
  return useMemo(() => mockThreats, []);
}

/**
 * Hook to get alert data for widgets
 */
export function useAlertData(): AlertType[] {
  return useMemo(() => mockAlerts, []);
}

/**
 * Hook to get system health data for widgets
 */
export function useSystemHealthData(): SystemHealthData {
  return useMemo(() => mockSystemHealth, []);
}
