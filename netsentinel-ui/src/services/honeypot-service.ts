import type { HoneypotServiceType } from '@/types';
import { mockConfig } from '@/test/__mocks__/mock-config';
import { generateMockHoneypots } from '@/mock/honeypot-mock';

/**
 * Get all honeypot services using dynamic mocking
 */
export async function getHoneypots(): Promise<HoneypotServiceType[]> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay
  await store.getGenerator('threats').delay(delayRange.min, delayRange.max);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('network');
  }

  // Generate dynamic honeypot services
  return generateMockHoneypots(10);
}

/**
 * Toggle honeypot service status
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function toggleHoneypot(_honeypotId: number): Promise<{ success: boolean }> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay
  await store.getGenerator('threats').delay(delayRange.min, delayRange.max);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('server');
  }

  return { success: true };
}
