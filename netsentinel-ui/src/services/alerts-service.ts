import type { AlertType } from '@/types';
import { mockConfig } from '@/test/__mocks__/mock-config';

/**
 * Get active alerts with dynamic data
 */
export async function getActiveAlerts(): Promise<AlertType[]> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay if enabled
  await store.getGenerator('alerts').delay(delayRange.min * 0.75, delayRange.max * 0.75);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('network');
  }

  const alerts = store.get<AlertType[]>('alerts', []);
  return alerts.filter(alert => !alert.acknowledged);
}

/**
 * Get all alerts with dynamic data
 */
export async function getAllAlerts(): Promise<AlertType[]> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay if enabled
  await store.getGenerator('alerts').delay(delayRange.min, delayRange.max);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('server');
  }

  // Generate fresh alerts if needed
  let alerts = store.get<AlertType[]>('alerts', []);
  if (alerts.length === 0) {
    const generator = store.getGenerator('alerts');
    alerts = generator.generateAlerts(8);
    store.set('alerts', alerts);
  }

  return alerts;
}

/**
 * Acknowledge an alert with state management
 */
export async function acknowledgeAlert(alertId: number): Promise<{ success: boolean }> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay if enabled
  await store.getGenerator('alerts').delay(delayRange.min, delayRange.max * 0.8);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('validation');
  }

  const alerts = store.get<AlertType[]>('alerts', []);
  const alertIndex = alerts.findIndex(a => a.id === alertId);

  if (alertIndex !== -1) {
    alerts[alertIndex] = {
      ...alerts[alertIndex],
      acknowledged: true,
      updated_at: store.getGenerator('alerts').getTimestamp()
    };
    store.set('alerts', alerts);
  }

  return { success: true };
}

/**
 * Resolve an alert with state management
 */
export async function resolveAlert(alertId: number): Promise<{ success: boolean }> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay if enabled
  await store.getGenerator('alerts').delay(delayRange.min * 1.25, delayRange.max);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('server');
  }

  const alerts = store.get<AlertType[]>('alerts', []);
  const alertIndex = alerts.findIndex(a => a.id === alertId);

  if (alertIndex !== -1) {
    // Remove resolved alert or mark as resolved
    alerts.splice(alertIndex, 1);
    store.set('alerts', alerts);
  }

  return { success: true };
}

/**
 * Create a new alert (for testing/simulating real-time alerts)
 */
export async function createAlert(alertData: Omit<AlertType, 'id' | 'created_at' | 'updated_at'>): Promise<AlertType> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay if enabled
  await store.getGenerator('alerts').delay(delayRange.min * 1.5, delayRange.max * 1.2);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('validation');
  }

  const alerts = store.get<AlertType[]>('alerts', []);
  const newAlert: AlertType = {
    ...alertData,
    id: Math.max(...alerts.map(a => a.id), 0) + 1,
    created_at: store.getGenerator('alerts').getTimestamp(),
    updated_at: store.getGenerator('alerts').getTimestamp(),
  };

  alerts.unshift(newAlert);
  store.set('alerts', alerts.slice(0, 50)); // Keep last 50 alerts

  return newAlert;
}
