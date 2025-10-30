import type { IncidentType, IncidentTimelineType } from '@/types';
import { faker } from '@faker-js/faker';

/**
 * Generate dynamic mock incidents
 */
export const generateMockIncidents = (count: number = 8): IncidentType[] => {
  const severities: Array<'low' | 'medium' | 'high' | 'critical'> = ['low', 'medium', 'high', 'critical'];
  const statuses: Array<'open' | 'investigating' | 'contained' | 'resolved' | 'closed'> = ['open', 'investigating', 'contained', 'resolved', 'closed'];
  const categories = [
    'Authentication Attack', 'Malware', 'Data Breach', 'DDoS Attack',
    'Phishing', 'Ransomware', 'Insider Threat', 'Configuration Error',
    'Supply Chain Attack', 'Zero-day Exploit'
  ];
  const teams = ['security-team', 'incident-response', 'network-team', 'admin'];

  return Array.from({ length: count }, (_, index) => {
    const severity = severities[Math.floor(Math.random() * severities.length)];
    const status = statuses[Math.floor(Math.random() * statuses.length)];
    const category = categories[Math.floor(Math.random() * categories.length)];
    const assignedTo = teams[Math.floor(Math.random() * teams.length)];

    let title: string;
    let description: string;
    let affectedSystems: string;
    let responsePlan: string;
    let containmentActions: string | null = null;
    let recoveryActions: string | null = null;
    let lessonsLearned: string | null = null;

    switch (category) {
      case 'Authentication Attack':
        title = `Brute Force Attack on ${faker.helpers.arrayElement(['SSH', 'FTP', 'Web Portal', 'API'])}`;
        description = `Multiple failed login attempts from ${faker.number.int({ min: 5, max: 50 })} IP addresses`;
        affectedSystems = faker.helpers.arrayElement(['SSH Service', 'Web Server', 'Database', 'API Gateway']);
        responsePlan = 'Block attacking IPs, implement rate limiting, strengthen authentication';
        break;
      case 'Malware':
        title = `${faker.helpers.arrayElement(['Trojan', 'Virus', 'Worm', 'Ransomware'])} Infection Detected`;
        description = `Malicious software detected attempting to ${faker.helpers.arrayElement(['encrypt files', 'steal data', 'spread to other systems', 'establish persistence'])}`;
        affectedSystems = faker.helpers.arrayElements(['Workstations', 'Servers', 'Network Shares', 'Email System'], { min: 1, max: 3 }).join(', ');
        responsePlan = 'Isolate affected systems, scan for malware, clean infections';
        break;
      case 'Data Breach':
        title = `Unauthorized Data Access in ${faker.helpers.arrayElement(['Customer Database', 'Employee Records', 'Financial Data', 'Intellectual Property'])}`;
        description = `Potential data exfiltration detected from sensitive systems`;
        affectedSystems = 'Database Server, Application Server';
        responsePlan = 'Secure affected systems, assess data exposure, notify stakeholders';
        break;
      case 'DDoS Attack':
        title = `Distributed Denial of Service Attack`;
        description = `High volume traffic from ${faker.number.int({ min: 1000, max: 50000 })} sources overwhelming network capacity`;
        affectedSystems = 'Load Balancer, Web Servers, Network Infrastructure';
        responsePlan = 'Activate DDoS mitigation, scale infrastructure, filter malicious traffic';
        break;
      default:
        title = `${category} Incident`;
        description = `Security incident involving ${category.toLowerCase()}`;
        affectedSystems = faker.helpers.arrayElement(['Multiple Systems', 'Critical Infrastructure', 'User Workstations']);
        responsePlan = 'Investigate incident, contain damage, implement remediation';
    }

    // Add actions based on status
    if (['contained', 'resolved', 'closed'].includes(status)) {
      containmentActions = faker.helpers.arrayElement([
        'Systems isolated from network',
        'Malicious processes terminated',
        'Firewall rules updated',
        'User accounts locked'
      ]);
    }

    if (['resolved', 'closed'].includes(status)) {
      recoveryActions = faker.helpers.arrayElement([
        'Systems restored from backup',
        'Security patches applied',
        'Password reset for affected accounts',
        'System monitoring increased'
      ]);

      lessonsLearned = faker.helpers.arrayElement([
        'Implement multi-factor authentication',
        'Regular security training required',
        'Update intrusion detection rules',
        'Improve backup procedures',
        'Enhance monitoring capabilities'
      ]);
    }

    const createdAt = new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000);
    const updatedAt = new Date(createdAt.getTime() + Math.random() * 7 * 24 * 60 * 60 * 1000);

    return {
      id: index + 1,
      title,
      severity,
      status,
      category,
      description,
      affected_systems: affectedSystems,
      assigned_to: assignedTo,
      response_plan: responsePlan,
      containment_actions: containmentActions,
      recovery_actions: recoveryActions,
      lessons_learned: lessonsLearned,
      created_at: createdAt.toISOString(),
      updated_at: updatedAt.toISOString()
    };
  });
};

/**
 * Mock incident data - dynamically generated
 */
export const mockIncidents: IncidentType[] = generateMockIncidents(10);

/**
 * Generate incident timeline for a specific incident
 */
export const generateIncidentTimeline = (incidentId: number, eventCount: number = 5): IncidentTimelineType[] => {
  const actionTypes = ['Detection', 'Investigation', 'Analysis', 'Containment', 'Recovery', 'Closure', 'Communication'];
  const performers = ['Automated System', 'security-team', 'incident-response', 'network-team', 'admin'];

  return Array.from({ length: eventCount }, (_, index) => {
    const actionType = actionTypes[Math.floor(Math.random() * actionTypes.length)];
    const performedBy = performers[Math.floor(Math.random() * performers.length)];

    let description: string;
    switch (actionType) {
      case 'Detection':
        description = `Initial detection of ${faker.helpers.arrayElement(['anomalous activity', 'security event', 'system compromise', 'unauthorized access'])}`;
        break;
      case 'Investigation':
        description = `Started ${faker.helpers.arrayElement(['forensic analysis', 'log review', 'system inspection', 'traffic analysis'])}`;
        break;
      case 'Analysis':
        description = `Completed ${faker.helpers.arrayElement(['threat assessment', 'impact analysis', 'root cause analysis', 'vulnerability assessment'])}`;
        break;
      case 'Containment':
        description = faker.helpers.arrayElement([
          'Blocked attacking IP addresses',
          'Isolated affected systems',
          'Disabled compromised accounts',
          'Updated firewall rules'
        ]);
        break;
      case 'Recovery':
        description = faker.helpers.arrayElement([
          'Restored systems from backup',
          'Applied security patches',
          'Reset compromised credentials',
          'Verified system integrity'
        ]);
        break;
      case 'Communication':
        description = `Notified ${faker.helpers.arrayElement(['management', 'stakeholders', 'customers', 'regulatory authorities'])} about incident`;
        break;
      default:
        description = `Performed ${actionType.toLowerCase()} action`;
    }

    return {
      id: Date.now() + index,
      incident_id: incidentId,
      action_type: actionType,
      description,
      performed_by: performedBy,
      created_at: new Date(Date.now() - (eventCount - index) * 60 * 60 * 1000).toISOString()
    };
  });
};

/**
 * Mock incident timeline data - dynamically generated
 */
export const mockIncidentTimeline: IncidentTimelineType[] = [
  ...generateIncidentTimeline(1, 6),
  ...generateIncidentTimeline(2, 4),
  ...generateIncidentTimeline(3, 3)
];

/**
 * Generate incidents by severity
 */
export const generateIncidentsBySeverity = (severity: 'low' | 'medium' | 'high' | 'critical', count: number = 3): IncidentType[] => {
  return Array.from({ length: count }, (_, index) => {
    const incident = generateMockIncidents(1)[0];
    return {
      ...incident,
      id: Date.now() + index,
      severity,
      title: `${severity.toUpperCase()} Severity: ${incident.category}`,
    };
  });
};

/**
 * Generate incidents by status
 */
export const generateIncidentsByStatus = (status: 'investigating' | 'contained' | 'resolved' | 'closed', count: number = 3): IncidentType[] => {
  return Array.from({ length: count }, (_, index) => {
    const incident = generateMockIncidents(1)[0];
    return {
      ...incident,
      id: Date.now() + index,
      status,
      containment_actions: ['contained', 'resolved', 'closed'].includes(status) ? 'Actions taken' : null,
      recovery_actions: ['resolved', 'closed'].includes(status) ? 'Recovery completed' : null,
      lessons_learned: status === 'closed' ? 'Lessons documented' : null,
    };
  });
};
