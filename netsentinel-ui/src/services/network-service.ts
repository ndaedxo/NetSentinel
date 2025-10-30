import type { NetworkTopology } from '@/types';
import { mockConfig } from '@/test/__mocks__/mock-config';
import { generateMockNetworkDevices, generateMockNetworkConnections } from '@/mock/network-mock';

/**
 * Get network topology data using dynamic mocking
 */
export async function getNetworkTopology(): Promise<NetworkTopology> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay
  await store.getGenerator('threats').delay(delayRange.min * 1.5, delayRange.max * 1.5);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('network');
  }

  // Generate dynamic network topology
  const devices = generateMockNetworkDevices(12);
  const connections = generateMockNetworkConnections(devices, 25);

  return {
    devices,
    connections
  };
}
