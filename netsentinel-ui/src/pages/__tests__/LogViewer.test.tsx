import { render, screen, fireEvent, waitFor } from '@/test/test-utils';
import LogViewer from '@/pages/LogViewer';

const mockGetLogs = jest.fn().mockResolvedValue([
  { id: '1', timestamp: new Date().toISOString(), level: 'info', source: 'ui', message: 'hello' },
]);
const mockSubscribe = jest.fn().mockImplementation((cb: any) => {
  const t = setTimeout(() => cb({ id: 'live', timestamp: new Date().toISOString(), level: 'warn', source: 'api', message: 'live' }), 10);
  return () => clearTimeout(t);
});

jest.mock('@/services', () => ({
  getLogs: (...a: any[]) => (mockGetLogs as any)(...a),
  subscribeLogs: (...a: any[]) => (mockSubscribe as any)(...a),
}));

describe('LogViewer', () => {
  it('loads logs, filters, and toggles live tail', async () => {
    render(<LogViewer />);

    await screen.findByText(/hello/);

    fireEvent.change(screen.getByDisplayValue('All Levels'), { target: { value: 'error' } });
    fireEvent.click(screen.getByText(/Run/i));
    await waitFor(() => expect(mockGetLogs).toHaveBeenCalled());

    // enable live tail
    fireEvent.click(screen.getByLabelText(/Live tail/i));
    await screen.findByText(/live/);
  });
});


