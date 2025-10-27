import type { HoneypotServiceType } from '@/types';
import { mockHoneypots } from '@/mock';

/**
 * Get all honeypot services
 */
export async function getHoneypots(): Promise<HoneypotServiceType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return mockHoneypots;
}

/**
 * Toggle honeypot service status
 */
export async function toggleHoneypot(_honeypotId: number): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return { success: true };
}
