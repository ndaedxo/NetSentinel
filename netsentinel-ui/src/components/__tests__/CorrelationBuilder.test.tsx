import { render, screen, fireEvent } from '@testing-library/react';
import CorrelationBuilder from '@/components/CorrelationBuilder';

describe('CorrelationBuilder', () => {
  it('adds a condition and updates DSL', () => {
    const onChange = jest.fn();
    render(<CorrelationBuilder onChange={onChange} />);

    // Add condition to default group
    fireEvent.click(screen.getByText(/Add Condition/i));
    // Change field of the new condition
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: 'ip' } });

    expect(onChange).toHaveBeenCalled();
  });
});


