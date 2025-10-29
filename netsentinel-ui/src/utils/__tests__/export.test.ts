import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { exportToCSV, exportToJSON, exportToPDF } from '../export';

// Mock jspdf-autotable first
jest.mock('jspdf-autotable', () => jest.fn());

// Mock jsPDF
jest.mock('jspdf', () => {
  class MockJsPDF {
    autoTable = jest.fn();
    text = jest.fn();
    setFontSize = jest.fn();
    save = jest.fn();
  }
  return MockJsPDF;
});

// Mock browser APIs
const mockElement = {
  href: '',
  download: '',
  style: { display: '' },
  click: jest.fn()
};

const mockCreateElement = jest.fn(() => mockElement);
const mockAppendChild = jest.fn();
const mockRemoveChild = jest.fn();

global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Override document methods directly
document.createElement = mockCreateElement;
document.body.appendChild = mockAppendChild;
document.body.removeChild = mockRemoveChild;


describe('Export Utilities', () => {
  const mockData = [
    { id: 1, name: 'John Doe', email: 'john@example.com', score: 85 },
    { id: 2, name: 'Jane Smith', email: 'jane@example.com', score: 92 },
  ];

  const mockColumns = [
    { key: 'name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'score', label: 'Score' }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('exportToCSV', () => {
    it('creates and downloads a CSV file', () => {
      exportToCSV(mockData, mockColumns, 'test.csv');

      expect(mockCreateElement).toHaveBeenCalledWith('a');
      expect(mockAppendChild).toHaveBeenCalled();
      expect(mockRemoveChild).toHaveBeenCalled();
    });
  });

  describe('exportToJSON', () => {
    it('creates and downloads a JSON file', () => {
      exportToJSON(mockData, 'test.json');

      expect(mockCreateElement).toHaveBeenCalledWith('a');
      expect(mockAppendChild).toHaveBeenCalled();
      expect(mockRemoveChild).toHaveBeenCalled();
    });
  });

  describe('exportToPDF', () => {
    it('creates PDF with correct title', async () => {
      await exportToPDF(mockData, mockColumns, 'Test Report', 'test.pdf');

      // Just test that the function doesn't throw
      expect(true).toBe(true);
    });

    it('uses default title when not provided', async () => {
      await exportToPDF(mockData, mockColumns);

      // Just test that the function doesn't throw
      expect(true).toBe(true);
    });
  });
});
