import type { NetworkTopology } from '@/types';
import { mockNetworkTopology } from '@/mock';

/**
 * Get network topology data
 */
export async function getNetworkTopology(): Promise<NetworkTopology> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 400));
  return mockNetworkTopology;
}
