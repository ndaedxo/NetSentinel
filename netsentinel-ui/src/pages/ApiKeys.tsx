import { useEffect, useState } from 'react';
import { PageLayout, ConfirmationModal, ScopeTagsInput } from '@/components';
import { listApiKeys, createApiKey, revokeApiKey } from '@/services';
import { useToast } from '@/hooks';
import type { ApiKeyItem } from '@/types';

export default function ApiKeys() {
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [items, setItems] = useState<ApiKeyItem[]>([]);
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState<string[]>(['read:*']);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<{ isOpen: boolean; keyId: string; keyName: string }>({
    isOpen: false,
    keyId: '',
    keyName: ''
  });
  const [validationErrors, setValidationErrors] = useState<{ name?: string; scopes?: string }>({});

  const { showToast } = useToast();

  const validateForm = () => {
    const errors: { name?: string; scopes?: string } = {};

    if (!name.trim()) {
      errors.name = 'Name is required';
    }

    if (scopes.length === 0) {
      errors.scopes = 'At least one scope is required';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const refresh = async () => {
    setLoading(true);
    const data = await listApiKeys();
    setItems(data);
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const onCreate = async () => {
    if (!validateForm()) {
      return;
    }

    setCreating(true);
    try {
      const resp = await createApiKey({ name, scopes });
      setNewKey(resp.key);
      setName('');
      setScopes(['read:*']);
      setValidationErrors({});
      await refresh();
      showToast('success', `API key "${name}" created successfully`);
    } catch {
      showToast('error', 'Failed to create API key');
    }
    setCreating(false);
  };

  const onRevokeClick = (id: string, name: string) => {
    setConfirmRevoke({ isOpen: true, keyId: id, keyName: name });
  };

  const onConfirmRevoke = async () => {
    try {
      await revokeApiKey(confirmRevoke.keyId);
      await refresh();
      showToast('success', `API key "${confirmRevoke.keyName}" has been revoked`);
    } catch {
      showToast('error', 'Failed to revoke API key');
    }
    setConfirmRevoke({ isOpen: false, keyId: '', keyName: '' });
  };

  const onCancelRevoke = () => {
    setConfirmRevoke({ isOpen: false, keyId: '', keyName: '' });
  };

  return (
    <PageLayout title="API Keys" subtitle="Manage access tokens for integrations">
      <div className="space-y-6">
        <section className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4">
          <h2 className="text-slate-200 text-sm font-semibold mb-3">Create API Key</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label htmlFor="api-key-name" className="sr-only">API Key Name</label>
              <input
                id="api-key-name"
                placeholder="Name (e.g., CI Pipeline)"
                className={`rounded bg-slate-800 border px-2 py-1 text-slate-200 w-full focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  validationErrors.name ? 'border-red-500 focus:ring-red-500' : 'border-slate-700'
                }`}
                value={name}
                onChange={(e) => setName(e.target.value)}
                aria-describedby={validationErrors.name ? "name-error" : undefined}
              />
              {validationErrors.name && (
                <p id="name-error" className="text-red-400 text-xs mt-1" role="alert">{validationErrors.name}</p>
              )}
            </div>
            <div>
              <label htmlFor="api-key-scopes" className="sr-only">API Key Scopes</label>
              <ScopeTagsInput
                value={scopes}
                onChange={setScopes}
                placeholder="Add scopes..."
                className={validationErrors.scopes ? 'border-red-500' : ''}
              />
              {validationErrors.scopes && (
                <p className="text-red-400 text-xs mt-1" role="alert">{validationErrors.scopes}</p>
              )}
            </div>
            <button
              disabled={creating}
              onClick={onCreate}
              className="px-3 py-2 rounded bg-blue-600 text-white disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:focus:ring-0"
            >
              {creating ? 'Creating...' : 'Create Key'}
            </button>
          </div>
          {newKey && (
            <div className="mt-3 text-xs text-slate-300 bg-slate-800 border border-slate-700 rounded p-2">
              <div className="font-semibold text-slate-200">New Key (shown once)</div>
              <div className="mt-1 font-mono break-all">{newKey}</div>
            </div>
          )}
        </section>

        <section className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4">
          <h2 className="text-slate-200 text-sm font-semibold mb-3">Existing Keys</h2>
          {loading ? (
            <div className="text-slate-400">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm" role="table" aria-label="API Keys">
                <thead className="text-slate-300">
                  <tr className="text-left" role="row">
                    <th className="px-2 py-2" scope="col" role="columnheader">Name</th>
                    <th className="px-2 py-2" scope="col" role="columnheader">Scopes</th>
                    <th className="px-2 py-2" scope="col" role="columnheader">Created</th>
                    <th className="px-2 py-2" scope="col" role="columnheader">Last Used</th>
                    <th className="px-2 py-2" scope="col" role="columnheader">Status</th>
                    <th className="px-2 py-2" scope="col" role="columnheader">Actions</th>
                  </tr>
                </thead>
                <tbody className="text-slate-300">
                  {items.map((k) => (
                    <tr key={k.id} className="border-t border-slate-800/80" role="row">
                      <td className="px-2 py-2">{k.name}</td>
                      <td className="px-2 py-2"><span className="font-mono text-xs break-all">{k.scopes.join(', ')}</span></td>
                      <td className="px-2 py-2">{new Date(k.createdAt).toLocaleString()}</td>
                      <td className="px-2 py-2">{k.lastUsedAt ? new Date(k.lastUsedAt).toLocaleString() : '—'}</td>
                      <td className="px-2 py-2">{k.revoked ? <span className="text-red-400">Revoked</span> : <span className="text-green-400">Active</span>}</td>
                      <td className="px-2 py-2">
                        <button disabled={k.revoked} onClick={() => onRevokeClick(k.id, k.name)} className="px-2 py-1 rounded bg-red-800 border border-red-700 hover:bg-red-700 disabled:opacity-50">Revoke</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <ConfirmationModal
        isOpen={confirmRevoke.isOpen}
        onClose={onCancelRevoke}
        onConfirm={onConfirmRevoke}
        title="Revoke API Key"
        message={`Are you sure you want to revoke the API key "${confirmRevoke.keyName}"? This action cannot be undone and the key will immediately become unusable.`}
        confirmText="Revoke Key"
        cancelText="Cancel"
        type="danger"
      />
    </PageLayout>
  );
}


