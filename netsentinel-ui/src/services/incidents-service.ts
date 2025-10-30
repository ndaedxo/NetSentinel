import type { IncidentType, IncidentTimelineType } from '@/types';
import { mockConfig } from '@/test/__mocks__/mock-config';
import { generateMockIncidents, generateIncidentTimeline } from '@/mock/incidents-mock';

/**
 * Get all incidents using dynamic mocking
 */
export async function getIncidents(): Promise<IncidentType[]> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay
  await store.getGenerator('alerts').delay(delayRange.min * 1.2, delayRange.max * 1.2);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('server');
  }

  // Generate dynamic incidents
  return generateMockIncidents(10);
}

/**
 * Get incident timeline for a specific incident using dynamic mocking
 */
export async function getIncidentTimeline(incidentId: number): Promise<IncidentTimelineType[]> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay
  await store.getGenerator('alerts').delay(delayRange.min * 0.8, delayRange.max * 0.8);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('network');
  }

  // Generate dynamic incident timeline
  return generateIncidentTimeline(incidentId, 5);
}

/**
 * Update incident status using dynamic mocking
 */
export async function updateIncidentStatus(): Promise<{ success: boolean }> {
  const store = mockConfig.getStore('alerts');
  const delayRange = mockConfig.getDelayRange('alerts');

  // Simulate realistic API delay
  await store.getGenerator('alerts').delay(delayRange.min * 1.5, delayRange.max * 1.5);

  // Check for simulated errors
  if (store.getGenerator('alerts').shouldError()) {
    throw store.getGenerator('alerts').generateError('validation');
  }

  return { success: true };
}
