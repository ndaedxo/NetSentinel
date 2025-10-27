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
export async function getIncidentTimeline(_incidentId: number): Promise<IncidentTimelineType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));
  return mockIncidentTimeline.filter(timeline => timeline.incident_id === _incidentId);
}

/**
 * Update incident status
 */
export async function updateIncidentStatus(
  _incidentId: number,
  _status: IncidentType['status']
): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return { success: true };
}
