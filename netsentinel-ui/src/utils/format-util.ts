/**
 * Formatting utility functions
 */

/**
 * Format a number with commas as thousands separators
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

/**
 * Format bytes to human-readable format (KB, MB, GB, etc.)
 */
export function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Format a percentage
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Truncate text to a maximum length with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Capitalize the first letter of a string
 */
export function capitalizeFirst(str: string): string {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Convert snake_case to Title Case
 */
export function snakeToTitleCase(str: string): string {
  return str
    .split('_')
    .map(word => capitalizeFirst(word))
    .join(' ');
}

/**
 * Convert camelCase to Title Case
 */
export function camelToTitleCase(str: string): string {
  return str
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, str => str.toUpperCase())
    .trim();
}

/**
 * Format a severity level for display
 */
export function formatSeverity(severity: 'low' | 'medium' | 'high' | 'critical'): string {
  return capitalizeFirst(severity);
}

/**
 * Format a status for display
 */
export function formatStatus(status: string): string {
  return capitalizeFirst(status.replace('_', ' '));
}

/**
 * Format connection count with appropriate suffix
 */
export function formatConnectionCount(count: number): string {
  if (count === 0) return 'No connections';
  if (count === 1) return '1 connection';
  return `${formatNumber(count)} connections`;
}

/**
 * Format threat count with appropriate suffix
 */
export function formatThreatCount(count: number): string {
  if (count === 0) return 'No threats';
  if (count === 1) return '1 threat';
  return `${formatNumber(count)} threats`;
}

/**
 * Format alert count with appropriate suffix
 */
export function formatAlertCount(count: number): string {
  if (count === 0) return 'No alerts';
  if (count === 1) return '1 alert';
  return `${formatNumber(count)} alerts`;
}

/**
 * Generate a random ID string
 */
export function generateId(length: number = 8): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Format a duration in seconds to human-readable format
 */
export function formatDurationFromSeconds(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;

  const parts = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (remainingSeconds > 0 || parts.length === 0) parts.push(`${remainingSeconds}s`);

  return parts.join(' ');
}
