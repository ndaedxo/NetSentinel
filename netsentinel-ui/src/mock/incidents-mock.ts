import type { IncidentType, IncidentTimelineType } from '@/types';

/**
 * Mock incident data
 */
export const mockIncidents: IncidentType[] = [
  {
    id: 1,
    title: "Brute Force Attack on SSH Service",
    severity: "high",
    status: "investigating",
    category: "Authentication Attack",
    description: "Multiple failed SSH login attempts from various IP addresses",
    affected_systems: "SSH Honeypot, Main Server",
    assigned_to: "security-team",
    response_plan: "Block attacking IPs, strengthen authentication",
    containment_actions: "IPs blocked via firewall",
    recovery_actions: "Monitor for additional attacks",
    lessons_learned: "Implement rate limiting on SSH",
    created_at: "2025-10-27T09:00:00Z",
    updated_at: "2025-10-27T10:00:00Z"
  },
  {
    id: 2,
    title: "Malware Distribution Attempt",
    severity: "critical",
    status: "contained",
    category: "Malware",
    description: "Attempted distribution of ransomware payload",
    affected_systems: "Web Server, File Share",
    assigned_to: "incident-response",
    response_plan: "Isolate affected systems, analyze malware",
    containment_actions: "Systems isolated from network",
    recovery_actions: "Clean systems, restore from backup",
    lessons_learned: "Improve endpoint protection",
    created_at: "2025-10-26T14:30:00Z",
    updated_at: "2025-10-27T08:00:00Z"
  }
];

/**
 * Mock incident timeline data
 */
export const mockIncidentTimeline: IncidentTimelineType[] = [
  {
    id: 1,
    incident_id: 1,
    action_type: "Detection",
    description: "Initial detection of brute force attempts",
    performed_by: "Automated System",
    created_at: "2025-10-27T09:00:00Z"
  },
  {
    id: 2,
    incident_id: 1,
    action_type: "Investigation",
    description: "Started forensic analysis of attack patterns",
    performed_by: "security-team",
    created_at: "2025-10-27T09:30:00Z"
  },
  {
    id: 3,
    incident_id: 1,
    action_type: "Containment",
    description: "Blocked attacking IP addresses",
    performed_by: "security-team",
    created_at: "2025-10-27T10:00:00Z"
  }
];
