import { mockApiKeys } from '@/mock';
import type { ApiKeyItem, CreateApiKeyRequest, CreateApiKeyResponse } from '@/types';

export async function listApiKeys(): Promise<ApiKeyItem[]> {
  await new Promise(r => setTimeout(r, 200));
  return [...mockApiKeys];
}

export async function createApiKey(req: CreateApiKeyRequest): Promise<CreateApiKeyResponse> {
  await new Promise(r => setTimeout(r, 300));
  const id = `key_${Math.random().toString(36).slice(2, 8)}`;
  const item: ApiKeyItem = {
    id,
    name: req.name,
    createdAt: new Date().toISOString(),
    scopes: req.scopes,
    revoked: false,
  };
  const key = `nsk_${Math.random().toString(36).slice(2)}.${Math.random().toString(36).slice(2)}`;
  // In a real impl, persist; here just push into mock for session feel
  mockApiKeys.push(item);
  return { key, item };
}

export async function revokeApiKey(id: string): Promise<{ success: boolean }> {
  await new Promise(r => setTimeout(r, 200));
  const idx = mockApiKeys.findIndex(k => k.id === id);
  if (idx >= 0) {
    mockApiKeys[idx] = { ...mockApiKeys[idx], revoked: true };
  }
  return { success: true };
}


