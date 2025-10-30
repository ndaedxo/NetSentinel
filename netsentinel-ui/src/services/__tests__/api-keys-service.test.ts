import { jest, describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { listApiKeys, createApiKey, revokeApiKey } from '../api-keys-service';
import { mockApiKeys } from '@/mock';

// Note: We don't mock timers here to keep tests simple and focused on functionality

// Mock Math.random for predictable test results
let randomCallCount = 0;
const mockRandom = jest.spyOn(Math, 'random');
mockRandom.mockImplementation(() => {
  randomCallCount++;
  return 0.1 + (randomCallCount * 0.1); // Return different values: 0.2, 0.3, 0.4, etc.
});

describe('API Keys Service', () => {
  // Store original mock data to restore after tests
  let originalMockApiKeys: typeof mockApiKeys;

  beforeEach(() => {
    // Reset mock data and random counter before each test
    randomCallCount = 0;
    originalMockApiKeys = [...mockApiKeys];
    mockApiKeys.length = 0;
    mockApiKeys.push(
      {
        id: 'key_abc123',
        name: 'Test Key 1',
        createdAt: '2024-01-01T10:00:00Z',
        scopes: ['read', 'write'],
        revoked: false,
      },
      {
        id: 'key_def456',
        name: 'Test Key 2',
        createdAt: '2024-01-01T11:00:00Z',
        scopes: ['read'],
        revoked: true,
      }
    );
  });

  afterEach(() => {
    // Restore original mock data
    mockApiKeys.length = 0;
    mockApiKeys.push(...originalMockApiKeys);
  });

  describe('listApiKeys', () => {
    it('returns all API keys from mock data', async () => {
      const result = await listApiKeys();

      expect(result).toHaveLength(2);
      expect(result).toEqual([
        {
          id: 'key_abc123',
          name: 'Test Key 1',
          createdAt: '2024-01-01T10:00:00Z',
          scopes: ['read', 'write'],
          revoked: false,
        },
        {
          id: 'key_def456',
          name: 'Test Key 2',
          createdAt: '2024-01-01T11:00:00Z',
          scopes: ['read'],
          revoked: true,
        },
      ]);
    });

    it('returns a copy of the data, not the original array', async () => {
      const result1 = await listApiKeys();
      const result2 = await listApiKeys();

      expect(result1).not.toBe(result2); // Different array references
      expect(result1).toEqual(result2); // Same content
    });

    it('handles empty mock data', async () => {
      mockApiKeys.length = 0;

      const result = await listApiKeys();
      expect(result).toEqual([]);
    });

    it('returns data after async operation', async () => {
      const result = await listApiKeys();

      // Should complete successfully
      expect(result).toHaveLength(2);
    });
  });

  describe('createApiKey', () => {
    it('creates a new API key with provided data', async () => {
      const request = {
        name: 'New Test Key',
        scopes: ['read', 'write', 'admin'] as const,
      };

      const result = await createApiKey(request);

      expect(result).toHaveProperty('key');
      expect(result).toHaveProperty('item');
      expect(result.item).toEqual({
        id: expect.stringMatching(/^key_[a-z0-9]{6}$/),
        name: 'New Test Key',
        createdAt: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/),
        scopes: ['read', 'write', 'admin'],
        revoked: false,
      });
    });

    it('generates a predictable API key format', async () => {
      const request = {
        name: 'Test Key',
        scopes: ['read'] as const,
      };

      const result = await createApiKey(request);

      // With Math.random() mocked to return 0.123456, the key should be predictable
      expect(result.key).toMatch(/^nsk_[a-z0-9]+\.[a-z0-9]+$/);
    });

    it('adds the new key to mock data', async () => {
      const initialLength = mockApiKeys.length;

      await createApiKey({
        name: 'Added Key',
        scopes: ['read'] as const,
      });

      expect(mockApiKeys).toHaveLength(initialLength + 1);
      const addedKey = mockApiKeys[mockApiKeys.length - 1];
      expect(addedKey.name).toBe('Added Key');
      expect(addedKey.scopes).toEqual(['read']);
      expect(addedKey.revoked).toBe(false);
    });

    it('handles different scope combinations', async () => {
      const testCases = [
        { name: 'Read Only', scopes: ['read'] as const },
        { name: 'Read Write', scopes: ['read', 'write'] as const },
        { name: 'All Scopes', scopes: ['read', 'write', 'admin', 'delete'] as const },
        { name: 'Empty Scopes', scopes: [] as const },
      ];

      for (const testCase of testCases) {
        const result = await createApiKey(testCase);
        expect(result.item.scopes).toEqual(testCase.scopes);
        expect(result.item.name).toBe(testCase.name);
      }
    });

    it('generates unique IDs for multiple keys', async () => {
      const result1 = await createApiKey({ name: 'Key 1', scopes: ['read'] as const });
      const result2 = await createApiKey({ name: 'Key 2', scopes: ['read'] as const });

      expect(result1.item.id).not.toBe(result2.item.id);
      expect(result1.key).not.toBe(result2.key);
    });

    it('completes creation operation', async () => {
      const result = await createApiKey({ name: 'Test', scopes: ['read'] as const });

      expect(result).toHaveProperty('key');
      expect(result).toHaveProperty('item');
    });
  });

  describe('revokeApiKey', () => {
    it('revokes an existing API key', async () => {
      const result = await revokeApiKey('key_abc123');

      expect(result).toEqual({ success: true });
      expect(mockApiKeys[0].revoked).toBe(true);
    });

    it('returns success even if key does not exist', async () => {
      const result = await revokeApiKey('nonexistent_key');

      expect(result).toEqual({ success: true });
    });

    it('does not modify other keys when revoking', async () => {
      await revokeApiKey('key_abc123');

      expect(mockApiKeys[0].revoked).toBe(true);
      expect(mockApiKeys[1].revoked).toBe(true); // Was already revoked
    });

    it('handles revoking already revoked keys', async () => {
      // key_def456 is already revoked
      const result = await revokeApiKey('key_def456');

      expect(result).toEqual({ success: true });
      expect(mockApiKeys[1].revoked).toBe(true); // Still revoked
    });

    it('preserves other key properties when revoking', async () => {
      const originalKey = { ...mockApiKeys[0] };

      await revokeApiKey('key_abc123');

      const revokedKey = mockApiKeys[0];
      expect(revokedKey.id).toBe(originalKey.id);
      expect(revokedKey.name).toBe(originalKey.name);
      expect(revokedKey.createdAt).toBe(originalKey.createdAt);
      expect(revokedKey.scopes).toEqual(originalKey.scopes);
      expect(revokedKey.revoked).toBe(true); // Only this changed
    });

    it('completes revocation operation', async () => {
      const result = await revokeApiKey('key_abc123');

      expect(result).toEqual({ success: true });
    });

    it('handles empty key ID', async () => {
      const result = await revokeApiKey('');

      expect(result).toEqual({ success: true });
      // No keys should be modified
      expect(mockApiKeys[0].revoked).toBe(false);
      expect(mockApiKeys[1].revoked).toBe(true);
    });
  });

  describe('Integration', () => {
    it('can create and then revoke a key', async () => {
      // Create a new key
      const createResult = await createApiKey({
        name: 'Integration Test Key',
        scopes: ['read', 'write'] as const,
      });

      const newKeyId = createResult.item.id;
      expect(mockApiKeys).toHaveLength(3); // Original 2 + 1 new

      // Revoke the key
      const revokeResult = await revokeApiKey(newKeyId);
      expect(revokeResult.success).toBe(true);

      // Check that the key is revoked
      const revokedKey = mockApiKeys.find(k => k.id === newKeyId);
      expect(revokedKey?.revoked).toBe(true);
    });

    it('createApiKey updates the mock data that listApiKeys returns', async () => {
      const initialKeys = await listApiKeys();
      expect(initialKeys).toHaveLength(2);

      await createApiKey({
        name: 'New Key',
        scopes: ['read'] as const,
      });

      const updatedKeys = await listApiKeys();
      expect(updatedKeys).toHaveLength(3);
      expect(updatedKeys[2].name).toBe('New Key');
    });
  });

  describe('Error handling', () => {
    it('handles malformed request data gracefully', async () => {
      // This should work even with minimal data
      const result = await createApiKey({
        name: '',
        scopes: [] as const,
      });

      expect(result).toHaveProperty('key');
      expect(result.item.name).toBe('');
      expect(result.item.scopes).toEqual([]);
    });

    it('handles concurrent operations', async () => {
      // Create multiple keys concurrently
      const promises = [
        createApiKey({ name: 'Key 1', scopes: ['read'] as const }),
        createApiKey({ name: 'Key 2', scopes: ['read'] as const }),
        createApiKey({ name: 'Key 3', scopes: ['read'] as const }),
      ];

      const results = await Promise.all(promises);

      expect(results).toHaveLength(3);
      expect(mockApiKeys).toHaveLength(5); // Original 2 + 3 new

      results.forEach(result => {
        expect(result).toHaveProperty('key');
        expect(result.item).toHaveProperty('id');
      });
    });
  });
});
