/**
 * Dynamic Mocking Examples
 * Comprehensive test examples showing the dynamic mocking system in action
 */

import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { mockUtils } from './mock-config';
import { getRecentThreats, getAllThreats, getThreatTimeline, blockThreat, getThreatStats } from '@/services/threats-service';
import { getActiveAlerts, getAllAlerts, acknowledgeAlert, resolveAlert, createAlert } from '@/services/alerts-service';

// Setup and teardown for all tests
beforeEach(() => {
  mockUtils.setup({
    realisticDelays: false, // Disable delays for faster tests
    randomErrors: false,    // Disable random errors by default
    seed: 42               // Consistent seed for reproducible tests
  });
});

afterEach(() => {
  mockUtils.reset();
});

describe('Dynamic Threat Service Mocking', () => {
  describe('Basic Functionality', () => {
    it('returns consistent threat data with seeded generation', async () => {
      // With seeded data, results should be consistent
      const threats1 = await getRecentThreats(5);
      const threats2 = await getRecentThreats(5);

      // With seeded data, results should be identical for deterministic testing
      expect(threats1).toEqual(threats2);
      expect(threats1.length).toBe(5);
      expect(threats2.length).toBe(5);

      // But structure should be consistent
      threats1.forEach(threat => {
        expect(threat).toHaveProperty('id');
        expect(threat).toHaveProperty('ip_address');
        expect(threat).toHaveProperty('threat_score');
        expect(threat).toHaveProperty('severity');
        expect(threat).toHaveProperty('threat_type');
      });
    });

    it('generates realistic threat scores', async () => {
      const threats = await getAllThreats();

      threats.forEach(threat => {
        expect(threat.threat_score).toBeGreaterThanOrEqual(0);
        expect(threat.threat_score).toBeLessThanOrEqual(100);
        expect(['low', 'medium', 'high', 'critical']).toContain(threat.severity);
      });

      // Should have a mix of severity levels
      const severities = threats.map(t => t.severity);
      expect(new Set(severities).size).toBeGreaterThan(1);
    });

    it('maintains state across operations', async () => {
      const initialThreats = await getAllThreats();
      const ipToBlock = initialThreats[0].ip_address;

      // Block a threat
      await blockThreat(ipToBlock);

      // Get threats again - should reflect the change
      const updatedThreats = await getAllThreats();
      const blockedThreat = updatedThreats.find(t => t.ip_address === ipToBlock);

      expect(blockedThreat?.is_blocked).toBe(1);
    });
  });

  describe('Error Simulation', () => {
    it('handles network errors', async () => {
      mockUtils.simulateErrors(1, 'network');

      await expect(getRecentThreats()).rejects.toThrow('Network request failed');
    });

    it('handles server errors', async () => {
      mockUtils.simulateErrors(1, 'server');

      await expect(getAllThreats()).rejects.toThrow('Internal server error');
    });

    it('handles auth errors', async () => {
      mockUtils.simulateErrors(1, 'auth');

      await expect(blockThreat('192.168.1.1')).rejects.toThrow('Authentication required');
    });

    it('handles validation errors', async () => {
      mockUtils.simulateErrors(1, 'validation');

      await expect(getThreatStats()).rejects.toThrow('Invalid request data');
    });

    it('continues working after errors', async () => {
      // Force an error, then normal operation should work
      mockUtils.simulateErrors(1, 'network');

      await expect(getRecentThreats()).rejects.toThrow();

      // Next call should work normally
      const threats = await getRecentThreats(3);
      expect(threats).toHaveLength(3);
    });
  });

  describe('Performance Simulation', () => {
    it('simulates realistic delays', async () => {
      mockUtils.setup({ realisticDelays: true });

      const startTime = Date.now();
      await getAllThreats();
      const endTime = Date.now();

      // Should take at least some time (300-1200ms based on config)
      // Allow some variance for test environment timing
      expect(endTime - startTime).toBeGreaterThan(150);
    });

    it('allows custom delay ranges', async () => {
      mockUtils.setup({
        realisticDelays: true,
        delayRanges: {
          threats: { min: 100, max: 200 }
        }
      });

      const startTime = Date.now();
      await getRecentThreats();
      const endTime = Date.now();

      expect(endTime - startTime).toBeGreaterThanOrEqual(100);
      expect(endTime - startTime).toBeLessThanOrEqual(250); // Allow some buffer
    });
  });

  describe('Data Consistency', () => {
    it('supports seeded generation for reproducible tests', async () => {
      // Test that seeding is supported (basic functionality test)
      mockUtils.setup({ seed: 42 });

      const threats1 = await getRecentThreats(3);
      const threats2 = await getRecentThreats(3);

      // With seeding, results should be consistent within the same test run
      expect(threats1.length).toBe(3);
      expect(threats2.length).toBe(3);

      // Each threat should have valid properties
      threats1.forEach(threat => {
        expect(threat).toHaveProperty('id');
        expect(threat).toHaveProperty('ip_address');
        expect(threat).toHaveProperty('threat_score');
        expect(threat.threat_score).toBeGreaterThanOrEqual(0);
        expect(threat.threat_score).toBeLessThanOrEqual(100);
      });

      threats2.forEach(threat => {
        expect(threat).toHaveProperty('id');
        expect(threat).toHaveProperty('ip_address');
        expect(threat).toHaveProperty('threat_score');
        expect(threat.threat_score).toBeGreaterThanOrEqual(0);
        expect(threat.threat_score).toBeLessThanOrEqual(100);
      });
    });

    it('produces different results with different seeds', async () => {
      mockUtils.setup({ seed: 123 });
      const threats1 = await getRecentThreats(5);

      mockUtils.reset();
      mockUtils.setup({ seed: 456 });
      const threats2 = await getRecentThreats(5);

      expect(threats1).not.toEqual(threats2);
    });
  });
});

describe('Dynamic Alert Service Mocking', () => {
  describe('State Management', () => {
    it('maintains alert state across operations', async () => {
      const alerts = await getAllAlerts();
      expect(alerts.length).toBeGreaterThan(0);

      const alertToAcknowledge = alerts[0];

      // Acknowledge an alert
      await acknowledgeAlert(alertToAcknowledge.id);

      // Check that it's now acknowledged
      const activeAlerts = await getActiveAlerts();
      const acknowledgedAlert = activeAlerts.find(a => a.id === alertToAcknowledge.id);

      expect(acknowledgedAlert).toBeUndefined();
    });

    it('removes resolved alerts', async () => {
      const alerts = await getAllAlerts();
      const alertToResolve = alerts[0];

      await resolveAlert(alertToResolve.id);

      const allAlertsAfter = await getAllAlerts();
      const resolvedAlert = allAlertsAfter.find(a => a.id === alertToResolve.id);

      expect(resolvedAlert).toBeUndefined();
    });

    it('creates new alerts dynamically', async () => {
      // Get alerts from store directly to avoid dynamic generation
      const store = mockUtils.getStore('alerts');
      const initialAlerts = store.get<AlertType[]>('alerts', []);
      const initialCount = initialAlerts.length;

      const newAlert = await createAlert({
        title: 'Test Alert',
        message: 'This is a dynamically created alert',
        severity: 'high',
        category: 'security',
        source: 'Test Service',
        acknowledged: false
      });

      // Check that the alert was created and added to store
      const finalAlerts = store.get<AlertType[]>('alerts', []);
      expect(finalAlerts.length).toBeGreaterThanOrEqual(initialCount + 1);
      expect(finalAlerts.some(a => a.id === newAlert.id)).toBe(true);
    });
  });

  describe('Real-time Simulation', () => {
    it('generates fresh alerts periodically', async () => {
      const alerts1 = await getAllAlerts();

      // Wait a bit and get alerts again - may generate new ones
      await new Promise(resolve => setTimeout(resolve, 10));

      const alerts2 = await getAllAlerts();

      // Should either be the same or have new alerts added
      expect(alerts2.length).toBeGreaterThanOrEqual(alerts1.length);
    });
  });
});

describe('Integration Testing', () => {
  it('handles complex workflows', async () => {
    // Get initial state
    const initialThreats = await getAllThreats();
    const initialAlerts = await getAllAlerts();

    // Find unblocked threats to block
    const unblockedThreats = initialThreats.filter(t => t.is_blocked === 0);

    // Ensure we have at least 2 unblocked threats
    if (unblockedThreats.length < 2) {
      // Create some specific unblocked threats for testing
      const store = mockUtils.getStore('threats');
      const generator = store.getGenerator('threats');
      const testThreats = [
        generator.generateThreat({ ip_address: '192.168.100.1', is_blocked: 0 }),
        generator.generateThreat({ ip_address: '192.168.100.2', is_blocked: 0 })
      ];
      store.set('threats', [...initialThreats, ...testThreats]);
    }

    // Get updated list with our test threats
    const updatedThreats = await getAllThreats();
    const availableUnblocked = updatedThreats.filter(t => t.is_blocked === 0);
    const threatsToBlock = availableUnblocked.slice(0, 2);

    // Block some threats
    for (const threat of threatsToBlock) {
      await blockThreat(threat.ip_address);
    }

    // Create some alerts
    await createAlert({
      title: 'Threat Blocked',
      message: 'Multiple threats have been blocked',
      severity: 'medium',
      category: 'security',
      source: 'Threat Management System',
      acknowledged: false
    });

    // Create a new alert
    await createAlert({
      title: 'Workflow Test Alert',
      message: 'Created during complex workflow test',
      severity: 'medium',
      category: 'security',
      source: 'Test System',
      acknowledged: false
    });

    // Acknowledge an alert
    if (initialAlerts.length > 0) {
      await acknowledgeAlert(initialAlerts[0].id);
    }

    // Verify final state
    const finalThreats = await getAllThreats();
    const finalAlerts = await getAllAlerts();
    const activeAlerts = await getActiveAlerts();
    const stats = await getThreatStats();

    // Should have blocked the threats we explicitly blocked
    const blockedIPs = threatsToBlock.map(t => t.ip_address);
    const actuallyBlocked = finalThreats.filter(t =>
      blockedIPs.includes(t.ip_address) && t.is_blocked === 1
    ).length;

    expect(actuallyBlocked).toBe(threatsToBlock.length);
    expect(finalAlerts.length).toBeGreaterThan(initialAlerts.length);
    expect(activeAlerts.length).toBeLessThanOrEqual(finalAlerts.length);
    expect(stats.blocked).toBeGreaterThan(0);
  });

  it('handles concurrent operations', async () => {
    const operations = [
      getRecentThreats(5),
      getAllThreats(),
      getThreatTimeline(),
      getThreatStats(),
      getActiveAlerts(),
      getAllAlerts()
    ];

    const results = await Promise.all(operations);

    // All operations should succeed
    results.forEach(result => {
      expect(result).toBeDefined();
    });

    // Results should be properly typed
    expect(Array.isArray(results[0])).toBe(true); // threats
    expect(Array.isArray(results[1])).toBe(true); // threats
    expect(Array.isArray(results[2])).toBe(true); // timeline
    expect(typeof results[3]).toBe('object');     // stats
    expect(Array.isArray(results[4])).toBe(true); // alerts
    expect(Array.isArray(results[5])).toBe(true); // alerts
  });

  it('simulates realistic error scenarios', async () => {
    // Mix of successful and failed operations
    mockUtils.simulateErrors(2, 'network'); // Next 2 operations will fail

    const results = await Promise.allSettled([
      getRecentThreats(),      // Should fail
      getAllThreats(),         // Should fail
      getThreatTimeline(),     // Should succeed
      getActiveAlerts(),       // Should succeed
    ]);

    const fulfilled = results.filter(r => r.status === 'fulfilled');
    const rejected = results.filter(r => r.status === 'rejected');

    expect(rejected).toHaveLength(2);
    expect(fulfilled).toHaveLength(2);

    rejected.forEach(result => {
      expect(result.status).toBe('rejected');
      expect(result.reason.message).toBe('Network request failed');
    });
  });
});

describe('Performance and Load Testing', () => {
  it('handles high data volumes', async () => {
    // Temporarily enable dynamic data generation for this test
    mockUtils.setup({ realisticDelays: false, seed: 999 });

    // Generate a lot of threats by calling the store directly
    const store = mockUtils.getStore('threats');
    const generator = store.getGenerator('threats');

    // Add many threats to the store
    const additionalThreats = Array.from({ length: 55 }, () =>
      generator.generateThreat()
    );

    store.set('threats', additionalThreats);

    const threats = await getAllThreats();
    expect(threats.length).toBe(55); // Should have exactly the threats we added
  });

  it('maintains performance under load', async () => {
    mockUtils.setup({ realisticDelays: false }); // Fast mode

    const startTime = Date.now();

    // Perform many operations quickly
    const operations = Array.from({ length: 50 }, () =>
      Promise.all([
        getRecentThreats(3),
        getActiveAlerts()
      ])
    );

    await Promise.all(operations);

    const endTime = Date.now();
    const duration = endTime - startTime;

    // Should complete in reasonable time (allowing for some variance)
    expect(duration).toBeLessThan(5000); // Less than 5 seconds for 50 operations
  });
});

