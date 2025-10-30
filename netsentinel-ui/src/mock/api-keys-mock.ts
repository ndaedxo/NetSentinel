// Mock API keys data
import type { ApiKeyItem } from '@/types';

export const mockApiKeys: ApiKeyItem[] = [
  {
    id: 'key_1',
    name: 'CI Pipeline',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
    lastUsedAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    scopes: ['read:threats', 'read:alerts', 'write:reports'],
    revoked: false,
  },
  {
    id: 'key_2',
    name: 'Read-only Dashboard',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
    scopes: ['read:*'],
    revoked: false,
  },
];


