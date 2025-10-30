/**
 * Dynamic Mock Data Generator
 * Creates realistic, varied mock data for testing
 */

import { faker } from '@faker-js/faker';
import type { ThreatType, AlertType } from '@/types';

// Configure faker for consistent results in tests
faker.seed(12345);

// Mock configuration interface
export interface MockConfig {
  /** Enable realistic delays */
  realisticDelays?: boolean;
  /** Enable random errors */
  randomErrors?: boolean;
  /** Error probability (0-1) */
  errorProbability?: number;
  /** Data variability factor */
  variability?: number;
  /** Enable time-based progression */
  timeBased?: boolean;
}

/**
 * Base mock generator class
 */
export class MockGenerator {
  private config: Required<MockConfig>;
  private startTime: number;

  constructor(config: MockConfig = {}) {
    this.config = {
      realisticDelays: config.realisticDelays ?? true,
      randomErrors: config.randomErrors ?? false,
      errorProbability: config.errorProbability ?? 0.05,
      variability: config.variability ?? 0.2,
      timeBased: config.timeBased ?? true,
      ...config
    };
    this.startTime = Date.now();
  }

  /**
   * Generate realistic delay
   */
  async delay(minMs: number = 100, maxMs: number = 1000): Promise<void> {
    if (!this.config.realisticDelays) return;

    const delay = faker.number.int({ min: minMs, max: maxMs });
    await new Promise(resolve => setTimeout(resolve, delay));
  }

  /**
   * Simulate random errors
   */
  shouldError(): boolean {
    if (!this.config.randomErrors) return false;
    return Math.random() < this.config.errorProbability;
  }

  /**
   * Generate error response
   */
  generateError(type: 'network' | 'auth' | 'validation' | 'server' = 'server'): Error {
    const errors = {
      network: new Error('Network request failed'),
      auth: new Error('Authentication required'),
      validation: new Error('Invalid request data'),
      server: new Error('Internal server error')
    };
    return errors[type];
  }

  /**
   * Apply variability to numeric values
   */
  varyNumber(base: number, factor?: number): number {
    const variability = factor ?? this.config.variability;
    const variation = base * variability;
    return faker.number.float({
      min: Math.max(0, base - variation),
      max: base + variation
    });
  }

  /**
   * Get current timestamp with optional offset
   */
  getTimestamp(offsetMinutes: number = 0): string {
    const now = this.config.timeBased ? Date.now() : this.startTime;
    const offsetMs = offsetMinutes * 60 * 1000;
    return new Date(now + offsetMs).toISOString();
  }

  /**
   * Generate realistic IP addresses
   */
  generateIP(): string {
    return faker.internet.ip();
  }

  /**
   * Generate threat score with realistic distribution
   */
  generateThreatScore(): number {
    // Bias towards lower scores (most threats are not critical)
    const rand = Math.random();
    if (rand < 0.6) return faker.number.int({ min: 20, max: 50 });
    if (rand < 0.85) return faker.number.int({ min: 51, max: 75 });
    if (rand < 0.95) return faker.number.int({ min: 76, max: 90 });
    return faker.number.int({ min: 91, max: 100 });
  }

  /**
   * Generate threat type
   */
  generateThreatType(): string {
    const types = [
      'Port Scan', 'Brute Force', 'Malware Download', 'SQL Injection',
      'XSS Attempt', 'DDoS Attack', 'Suspicious Login', 'Data Exfiltration',
      'Ransomware', 'Phishing', 'Zero-day Exploit', 'Credential Stuffing'
    ];
    return faker.helpers.arrayElement(types);
  }

  /**
   * Generate country code
   */
  generateCountryCode(): string {
    const countries = ['US', 'CN', 'RU', 'IN', 'BR', 'DE', 'FR', 'JP', 'KR', 'GB', 'CA', 'AU'];
    return faker.helpers.arrayElement(countries);
  }

  /**
   * Generate severity based on threat score
   */
  generateSeverity(score: number): 'low' | 'medium' | 'high' | 'critical' {
    if (score >= 90) return 'critical';
    if (score >= 75) return 'high';
    if (score >= 50) return 'medium';
    return 'low';
  }

  /**
   * Generate service name
   */
  generateService(): string {
    const services = [
      'SSH Honeypot', 'FTP Honeypot', 'HTTP Honeypot', 'SMTP Honeypot',
      'Database Honeypot', 'Web Server Honeypot', 'API Gateway', 'Load Balancer'
    ];
    return faker.helpers.arrayElement(services);
  }
}

/**
 * Threat Data Generator
 */
export class ThreatGenerator extends MockGenerator {
  private threatIdCounter = 1;

  /**
   * Generate a single threat
   */
  generateThreat(overrides: Partial<ThreatType> = {}): ThreatType {
    const score = overrides.threat_score ?? this.generateThreatScore();
    const createdAt = this.getTimestamp(faker.number.int({ min: -1440, max: 0 })); // Last 24 hours

    return {
      id: this.threatIdCounter++,
      ip_address: overrides.ip_address ?? this.generateIP(),
      country_code: overrides.country_code ?? this.generateCountryCode(),
      threat_score: score,
      severity: overrides.severity ?? this.generateSeverity(score),
      threat_type: overrides.threat_type ?? this.generateThreatType(),
      description: overrides.description ?? faker.lorem.sentence(),
      honeypot_service: overrides.honeypot_service ?? this.generateService(),
      is_blocked: overrides.is_blocked ?? faker.datatype.boolean() ? 1 : 0,
      created_at: createdAt,
      updated_at: overrides.updated_at ?? createdAt,
      ...overrides
    };
  }

  /**
   * Generate multiple threats
   */
  generateThreats(count: number, overrides: Partial<ThreatType> = {}): ThreatType[] {
    return Array.from({ length: count }, () => this.generateThreat(overrides));
  }

  /**
   * Generate timeline data points
   */
  generateTimelineData(hours: number = 24): Array<{timestamp: string; threat_count: number; blocked_count: number}> {
    const dataPoints: Array<{timestamp: string; threat_count: number; blocked_count: number}> = [];

    for (let i = hours; i >= 0; i--) {
      const baseThreats = this.varyNumber(20, 0.5);
      const threats = Math.max(0, Math.floor(baseThreats));
      const blockedRatio = 0.7 + Math.random() * 0.25; // 70-95% blocked
      const blocked = Math.floor(threats * blockedRatio);

      dataPoints.push({
        timestamp: this.getTimestamp(-i * 60), // Every hour
        threat_count: threats,
        blocked_count: blocked
      });
    }

    return dataPoints;
  }

  /**
   * Generate recent threats (last few hours)
   */
  generateRecentThreats(count: number = 5): ThreatType[] {
    return this.generateThreats(count).sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }
}

/**
 * Alert Data Generator
 */
export class AlertGenerator extends MockGenerator {
  private alertIdCounter = 1;

  /**
   * Generate a single alert
   */
  generateAlert(overrides: Partial<AlertType> = {}): AlertType {
    const severity = overrides.severity ?? faker.helpers.arrayElement(['low', 'medium', 'high', 'critical'] as const);
    const acknowledged = overrides.acknowledged ?? faker.datatype.boolean();
    const createdAt = this.getTimestamp(faker.number.int({ min: -360, max: 0 })); // Last 6 hours

    return {
      id: this.alertIdCounter++,
      title: overrides.title ?? faker.lorem.words(3),
      message: overrides.message ?? faker.lorem.sentence(),
      severity,
      status: overrides.status ?? (acknowledged ? 'acknowledged' as const : 'new' as const),
      category: overrides.category ?? faker.helpers.arrayElement(['security', 'system', 'network', 'performance']),
      source: overrides.source ?? this.generateService(),
      acknowledged,
      is_acknowledged: acknowledged ? 1 : 0,
      threat_id: overrides.threat_id ?? this.alertIdCounter,
      created_at: createdAt,
      updated_at: overrides.updated_at ?? createdAt,
      ...overrides
    };
  }

  /**
   * Generate multiple alerts
   */
  generateAlerts(count: number): AlertType[] {
    return Array.from({ length: count }, () => this.generateAlert());
  }
}

/**
 * Stateful Mock Store
 * Maintains state across mock calls
 */
export class MockStore {
  private state: Map<string, unknown> = new Map();
  private generators: Map<string, MockGenerator> = new Map();

  constructor() {
    this.generators.set('threats', new ThreatGenerator());
    this.generators.set('alerts', new AlertGenerator());
  }

  /**
   * Get or create generator
   */
  getGenerator<T extends MockGenerator>(type: string): T {
    return this.generators.get(type) as T;
  }

  /**
   * Get state value
   */
  get<T>(key: string, defaultValue?: T): T {
    return this.state.get(key) ?? defaultValue;
  }

  /**
   * Set state value
   */
  set<T>(key: string, value: T): void {
    this.state.set(key, value);
  }

  /**
   * Update state value
   */
  update<T>(key: string, updater: (current: T | undefined) => T): void {
    const current = this.state.get(key);
    this.state.set(key, updater(current));
  }

  /**
   * Reset state and create fresh generators
   */
  reset(): void {
    this.state.clear();
    // Create fresh generators to avoid state pollution between tests
    this.generators.clear();
    this.generators.set('threats', new ThreatGenerator());
    this.generators.set('alerts', new AlertGenerator());
  }

  /**
   * Get all threats with state management
   */
  getAllThreats(): ThreatType[] {
    const generator = this.getGenerator<ThreatGenerator>('threats');
    let threats = this.get<ThreatType[]>('threats', []);

    // Ensure we have some initial data
    if (threats.length === 0) {
      threats = generator.generateThreats(10);
      this.set('threats', threats);
    }

    // Add new threats periodically (but not in tests to ensure predictability)
    if (process.env.NODE_ENV !== 'test' && Math.random() < 0.3) { // 30% chance of new threat
      const newThreat = generator.generateThreat();
      threats = [newThreat, ...threats].slice(0, 50); // Keep last 50 threats
      this.set('threats', threats);
    }

    return threats;
  }

  /**
   * Get recent threats
   */
  getRecentThreats(count: number = 10): ThreatType[] {
    const allThreats = this.getAllThreats();
    return allThreats.slice(0, count);
  }

  /**
   * Get timeline data
   */
  getTimelineData(): Array<{timestamp: string; threat_count: number; blocked_count: number}> {
    const generator = this.getGenerator<ThreatGenerator>('threats');
    return generator.generateTimelineData();
  }

  /**
   * Block a threat
   */
  blockThreat(ipAddress: string): { success: boolean } {
    const threats = this.get<ThreatType[]>('threats', []);
    const threatIndex = threats.findIndex(t => t.ip_address === ipAddress);

    if (threatIndex !== -1) {
      threats[threatIndex] = { ...threats[threatIndex], is_blocked: 1 };
      this.set('threats', threats);
    }

    return { success: true };
  }
}

// Global mock store instance
export const mockStore = new MockStore();

// Export individual generators for direct use
export const threatGenerator = new ThreatGenerator();
export const alertGenerator = new AlertGenerator();

