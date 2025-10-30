export interface ApiKeyItem {
  id: string;
  name: string;
  createdAt: string;
  lastUsedAt?: string;
  scopes: string[];
  revoked: boolean;
}

export interface CreateApiKeyRequest {
  name: string;
  scopes: string[];
}

export interface CreateApiKeyResponse {
  key: string; // display once
  item: ApiKeyItem;
}


