import { describe, it, expect } from '@jest/globals';
import {
  formatNumber,
  formatBytes,
  formatPercentage,
  truncateText,
  capitalizeFirst,
  snakeToTitleCase,
  camelToTitleCase,
  formatSeverity,
  formatStatus,
  formatConnectionCount,
  formatThreatCount,
  formatAlertCount,
  generateId,
  formatDurationFromSeconds
} from '../format-util';

describe('Format Utilities', () => {
  describe('formatNumber', () => {
    it('formats numbers with commas', () => {
      expect(formatNumber(1000)).toBe('1,000');
      expect(formatNumber(1234567)).toBe('1,234,567');
      expect(formatNumber(42)).toBe('42');
    });
  });

  describe('formatBytes', () => {
    it('formats bytes correctly', () => {
      expect(formatBytes(0)).toBe('0 Bytes');
      expect(formatBytes(1024)).toBe('1 KB');
      expect(formatBytes(1024 * 1024)).toBe('1 MB');
      expect(formatBytes(1024 * 1024 * 1024)).toBe('1 GB');
      expect(formatBytes(1024 * 1024 * 1024 * 1024)).toBe('1 TB');
    });

    it('handles different decimal places', () => {
      expect(formatBytes(1500, 0)).toBe('1 KB');
      expect(formatBytes(1536, 2)).toBe('1.5 KB');
    });
  });

  describe('formatPercentage', () => {
    it('formats percentages correctly', () => {
      expect(formatPercentage(0.5)).toBe('50.0%');
      expect(formatPercentage(0.123, 2)).toBe('12.30%');
      expect(formatPercentage(1, 0)).toBe('100%');
    });
  });

  describe('truncateText', () => {
    it('truncates text longer than max length', () => {
      expect(truncateText('Hello World', 5)).toBe('He...');
      expect(truncateText('Short', 10)).toBe('Short');
      expect(truncateText('Exactly eight', 15)).toBe('Exactly eight');
    });
  });

  describe('capitalizeFirst', () => {
    it('capitalizes the first letter and lowercases the rest', () => {
      expect(capitalizeFirst('hello')).toBe('Hello');
      expect(capitalizeFirst('HELLO')).toBe('Hello');
      expect(capitalizeFirst('')).toBe('');
      expect(capitalizeFirst('a')).toBe('A');
    });
  });

  describe('snakeToTitleCase', () => {
    it('converts snake_case to Title Case', () => {
      expect(snakeToTitleCase('hello_world')).toBe('Hello World');
      expect(snakeToTitleCase('user_name')).toBe('User Name');
      expect(snakeToTitleCase('single')).toBe('Single');
    });
  });

  describe('camelToTitleCase', () => {
    it('converts camelCase to Title Case', () => {
      expect(camelToTitleCase('helloWorld')).toBe('Hello World');
      expect(camelToTitleCase('userName')).toBe('User Name');
      expect(camelToTitleCase('single')).toBe('Single');
      expect(camelToTitleCase('XMLHttpRequest')).toBe('XMLHttp Request');
    });
  });

  describe('formatSeverity', () => {
    it('formats severity levels', () => {
      expect(formatSeverity('low')).toBe('Low');
      expect(formatSeverity('medium')).toBe('Medium');
      expect(formatSeverity('high')).toBe('High');
      expect(formatSeverity('critical')).toBe('Critical');
    });
  });

  describe('formatStatus', () => {
    it('formats status strings', () => {
      expect(formatStatus('active')).toBe('Active');
      expect(formatStatus('in_progress')).toBe('In Progress');
      expect(formatStatus('not_found')).toBe('Not Found');
    });
  });

  describe('formatConnectionCount', () => {
    it('formats connection counts correctly', () => {
      expect(formatConnectionCount(0)).toBe('No connections');
      expect(formatConnectionCount(1)).toBe('1 connection');
      expect(formatConnectionCount(5)).toBe('5 connections');
      expect(formatConnectionCount(1234)).toBe('1,234 connections');
    });
  });

  describe('formatThreatCount', () => {
    it('formats threat counts correctly', () => {
      expect(formatThreatCount(0)).toBe('No threats');
      expect(formatThreatCount(1)).toBe('1 threat');
      expect(formatThreatCount(5)).toBe('5 threats');
      expect(formatThreatCount(1234)).toBe('1,234 threats');
    });
  });

  describe('formatAlertCount', () => {
    it('formats alert counts correctly', () => {
      expect(formatAlertCount(0)).toBe('No alerts');
      expect(formatAlertCount(1)).toBe('1 alert');
      expect(formatAlertCount(5)).toBe('5 alerts');
      expect(formatAlertCount(1234)).toBe('1,234 alerts');
    });
  });

  describe('generateId', () => {
    it('generates IDs of specified length', () => {
      expect(generateId(8)).toHaveLength(8);
      expect(generateId(16)).toHaveLength(16);
      expect(generateId(4)).toHaveLength(4);
    });

    it('generates unique IDs', () => {
      const id1 = generateId(10);
      const id2 = generateId(10);
      expect(id1).not.toBe(id2);
    });

    it('uses only alphanumeric characters', () => {
      const id = generateId(100);
      expect(id).toMatch(/^[A-Za-z0-9]+$/);
    });
  });

  describe('formatDurationFromSeconds', () => {
    it('formats durations correctly', () => {
      expect(formatDurationFromSeconds(30)).toBe('30s');
      expect(formatDurationFromSeconds(90)).toBe('1m 30s');
      expect(formatDurationFromSeconds(3661)).toBe('1h 1m 1s');
      expect(formatDurationFromSeconds(7323)).toBe('2h 2m 3s');
    });

    it('handles edge cases', () => {
      expect(formatDurationFromSeconds(0)).toBe('0s');
      expect(formatDurationFromSeconds(59)).toBe('59s');
      expect(formatDurationFromSeconds(60)).toBe('1m 0s');
      expect(formatDurationFromSeconds(3600)).toBe('1h 0m 0s');
    });
  });
});
