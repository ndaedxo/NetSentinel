import type { ThreatType } from '@/types';
import { threatGenerator } from '@/test/__mocks__/mock-generator';

interface ThreatTimelineData {
  timestamp: string;
  threat_count: number;
  blocked_count: number;
}

/**
 * Generate dynamic mock threat data with realistic variety
 */
export const generateMockThreats = (count: number = 20): ThreatType[] => {
  return Array.from({ length: count }, (_, index) => {
    const threat = threatGenerator.generateThreat();
    return {
      ...threat,
      id: index + 1,
      is_blocked: index % 3 === 0 ? 1 : 0, // Some blocked, some not
    };
  });
};

/**
 * Mock threat data - dynamically generated for realistic testing
 */
export const mockThreats: ThreatType[] = generateMockThreats(25);

/**
 * Mock recent threats (subset of all threats) - dynamically generated
 */
export const mockRecentThreats: ThreatType[] = mockThreats
  .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  .slice(0, 10);

/**
 * Mock threat timeline data - dynamically generated
 */
export const mockThreatTimeline: ThreatTimelineData[] = threatGenerator.generateTimelineData(24);

/**
 * Generate threats with specific criteria
 */
export const generateThreatsBySeverity = (severity: 'low' | 'medium' | 'high' | 'critical', count: number = 8): ThreatType[] => {
  return Array.from({ length: count }, (_, index) => {
    const threat = threatGenerator.generateThreat({ severity });
    return {
      ...threat,
      id: Date.now() + index,
      is_blocked: Math.random() > 0.5 ? 1 : 0,
    };
  });
};

/**
 * Generate threats by threat type
 */
export const generateThreatsByType = (threatType: string, count: number = 6): ThreatType[] => {
  return Array.from({ length: count }, (_, index) => {
    const threat = threatGenerator.generateThreat({ threat_type: threatType });
    return {
      ...threat,
      id: Date.now() + index,
      is_blocked: Math.random() > 0.6 ? 1 : 0,
    };
  });
};

/**
 * Generate threats from specific countries
 */
export const generateThreatsByCountry = (countryCode: string, count: number = 5): ThreatType[] => {
  return Array.from({ length: count }, (_, index) => {
    const threat = threatGenerator.generateThreat({ country_code: countryCode });
    return {
      ...threat,
      id: Date.now() + index,
      is_blocked: Math.random() > 0.5 ? 1 : 0,
    };
  });
};

/**
 * Generate blocked threats
 */
export const generateBlockedThreats = (count: number = 10): ThreatType[] => {
  return Array.from({ length: count }, (_, index) => {
    const threat = threatGenerator.generateThreat();
    return {
      ...threat,
      id: Date.now() + index,
      is_blocked: 1,
    };
  });
};

/**
 * Generate active (unblocked) threats
 */
export const generateActiveThreats = (count: number = 12): ThreatType[] => {
  return Array.from({ length: count }, (_, index) => {
    const threat = threatGenerator.generateThreat();
    return {
      ...threat,
      id: Date.now() + index,
      is_blocked: 0,
    };
  });
};
