import { render, screen, fireEvent, waitFor } from '@/test/test-utils';
import NotificationSettings from '@/pages/NotificationSettings';

// Simplify layout to avoid unrelated DOM
jest.mock('@/components', () => ({
  PageLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock('@/services', () => ({
  getNotificationPreferences: jest.fn().mockResolvedValue({
    emailEnabled: true,
    smsEnabled: false,
    slackEnabled: false,
    severities: ['high','critical'],
  }),
  getChannelConfig: jest.fn().mockResolvedValue({ email: { from: 'alerts@test.local' } }),
  updateNotificationPreferences: jest.fn().mockResolvedValue({}),
  updateChannelConfig: jest.fn().mockResolvedValue({}),
}));

describe('NotificationSettings', () => {
  it('loads and can save settings', async () => {
    render(<NotificationSettings />);
    // shows loading then content
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
    await screen.findByText(/Channels/i);

    const saveBtn = screen.getByRole('button', { name: /Save Settings/i });
    fireEvent.click(saveBtn);

    await waitFor(() => expect(saveBtn).toBeEnabled());
  });
});


