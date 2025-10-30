import { render, screen, fireEvent, waitFor } from '@/test/test-utils';
import ApiKeys from '@/pages/ApiKeys';

const mockList = jest.fn().mockResolvedValue([
  { id: 'k1', name: 'Existing', createdAt: new Date().toISOString(), scopes: ['read:*'], revoked: false },
]);
const mockCreate = jest.fn().mockResolvedValue({ key: 'nsk_abc.123', item: { id: 'k2', name: 'New', createdAt: new Date().toISOString(), scopes: ['read:*'], revoked: false }});
const mockRevoke = jest.fn().mockResolvedValue({ success: true });

jest.mock('@/services', () => ({
  listApiKeys: (...args: any[]) => (mockList as any)(...args),
  createApiKey: (...args: any[]) => (mockCreate as any)(...args),
  revokeApiKey: (...args: any[]) => (mockRevoke as any)(...args),
}));

describe('ApiKeys', () => {
  it('lists keys, creates a key, and shows one-time key', async () => {
    render(<ApiKeys />);

    await screen.findByText(/Existing Keys/i);
    expect(screen.getByText('Existing')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/Name/i), { target: { value: 'CI' } });
    fireEvent.click(screen.getByRole('button', { name: /Create Key/i }));

    await waitFor(() => expect(mockCreate).toHaveBeenCalled());

    // Revoke existing key
    fireEvent.click(screen.getAllByText(/Revoke/i)[0]);

    // Confirm the revocation in the modal
    await screen.findByText('Revoke API Key');
    fireEvent.click(screen.getByText('Revoke Key'));

    await waitFor(() => expect(mockRevoke).toHaveBeenCalled());
  });
});


