import type { IncidentType, IncidentTimelineType } from '@/types';
import { mockIncidents, mockIncidentTimeline } from '@/mock';

/**
 * Get all incidents
 */
export async function getIncidents(): Promise<IncidentType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return mockIncidents;
}

/**
 * Get incident timeline for a specific incident
 */
export async function getIncidentTimeline(incidentId: number): Promise<IncidentTimelineType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));
  return mockIncidentTimeline.filter(timeline => timeline.incident_id === incidentId);
}

/**
 * Update incident status
 */
export async function updateIncidentStatus(): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return { success: true };
}
