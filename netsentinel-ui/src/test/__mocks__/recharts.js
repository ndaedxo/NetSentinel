// Mock for recharts library
const React = require('react');

const MockComponent = ({ children, ...props }) =>
  React.createElement('div', {
    'data-testid': 'mock-chart',
    ...props
  }, children || 'Mock Chart');

module.exports = {
  AreaChart: MockComponent,
  Area: MockComponent,
  XAxis: MockComponent,
  YAxis: MockComponent,
  CartesianGrid: MockComponent,
  Tooltip: MockComponent,
  ResponsiveContainer: ({ children, ...props }) =>
    React.createElement('div', {
      'data-testid': 'mock-responsive-container',
      ...props
    }, children),
  LineChart: MockComponent,
  Line: MockComponent,
  BarChart: MockComponent,
  Bar: MockComponent,
  PieChart: MockComponent,
  Pie: MockComponent,
  Cell: MockComponent,
  Legend: MockComponent,
};
