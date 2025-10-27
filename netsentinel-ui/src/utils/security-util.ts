/**
 * Security and threat-related utility functions
 */

/**
 * Validate if a string is a valid IPv4 address
 */
export function isValidIPv4(ip: string): boolean {
  const ipv4Regex = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
  const match = ip.match(ipv4Regex);

  if (!match) return false;

  return match.slice(1).every(octet => {
    const num = parseInt(octet, 10);
    return num >= 0 && num <= 255;
  });
}

/**
 * Validate if a string is a valid IPv6 address
 */
export function isValidIPv6(ip: string): boolean {
  const ipv6Regex = /^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$/;

  return ipv6Regex.test(ip);
}

/**
 * Validate if a string is a valid IP address (IPv4 or IPv6)
 */
export function isValidIP(ip: string): boolean {
  return isValidIPv4(ip) || isValidIPv6(ip);
}

/**
 * Get threat level CSS classes based on severity
 */
export function getThreatColorClasses(severity: 'low' | 'medium' | 'high' | 'critical'): string {
  switch (severity) {
    case 'low':
      return "bg-blue-500/20 text-blue-300 border-blue-500/30";
    case 'medium':
      return "bg-yellow-500/20 text-yellow-300 border-yellow-500/30";
    case 'high':
      return "bg-orange-500/20 text-orange-300 border-orange-500/30";
    case 'critical':
      return "bg-red-500/20 text-red-300 border-red-500/30";
    default:
      return "bg-gray-500/20 text-gray-300 border-gray-500/30";
  }
}

/**
 * Get threat level CSS classes for modal/header displays
 */
export function getThreatModalColorClasses(severity: 'low' | 'medium' | 'high' | 'critical'): string {
  switch (severity) {
    case 'low':
      return "text-blue-400 border-blue-500/30 bg-blue-500/10";
    case 'medium':
      return "text-yellow-400 border-yellow-500/30 bg-yellow-500/10";
    case 'high':
      return "text-orange-400 border-orange-500/30 bg-orange-500/10";
    case 'critical':
      return "text-red-400 border-red-500/30 bg-red-500/10";
    default:
      return "text-gray-400 border-gray-500/30 bg-gray-500/10";
  }
}

/**
 * Get threat level border-left color for alerts
 */
export function getThreatBorderColor(severity: 'low' | 'medium' | 'high' | 'critical'): string {
  switch (severity) {
    case 'low':
      return "border-blue-500";
    case 'medium':
      return "border-yellow-500";
    case 'high':
      return "border-orange-500";
    case 'critical':
      return "border-red-500";
    default:
      return "border-gray-500";
  }
}

/**
 * Get threat level color hex value based on severity
 */
export function getThreatColor(severity: 'low' | 'medium' | 'high' | 'critical'): string {
  switch (severity) {
    case 'low':
      return '#3B82F6'; // blue
    case 'medium':
      return '#F59E0B'; // yellow
    case 'high':
      return '#F97316'; // orange
    case 'critical':
      return '#EF4444'; // red
    default:
      return '#6B7280'; // gray
  }
}

/**
 * Get threat level numeric value for sorting
 */
export function getThreatLevelValue(severity: 'low' | 'medium' | 'high' | 'critical'): number {
  switch (severity) {
    case 'low':
      return 1;
    case 'medium':
      return 2;
    case 'high':
      return 3;
    case 'critical':
      return 4;
    default:
      return 0;
  }
}

/**
 * Calculate risk score based on multiple factors
 */
export function calculateRiskScore(
  threatScore: number,
  severity: 'low' | 'medium' | 'high' | 'critical',
  isBlocked: boolean,
  timeSinceDetection: number // in hours
): number {
  let score = threatScore;

  // Apply severity multiplier
  const severityMultiplier = getThreatLevelValue(severity) * 0.25;
  score *= (1 + severityMultiplier);

  // Reduce score if blocked
  if (isBlocked) {
    score *= 0.7;
  }

  // Increase score based on recency (newer threats are riskier)
  if (timeSinceDetection < 1) {
    score *= 1.3; // Last hour
  } else if (timeSinceDetection < 24) {
    score *= 1.1; // Last 24 hours
  }

  return Math.round(score * 100) / 100;
}

/**
 * Check if an IP address is private
 */
export function isPrivateIP(ip: string): boolean {
  if (!isValidIPv4(ip)) return false;

  const octets = ip.split('.').map(Number);

  // 10.0.0.0/8
  if (octets[0] === 10) return true;

  // 172.16.0.0/12
  if (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) return true;

  // 192.168.0.0/16
  if (octets[0] === 192 && octets[1] === 168) return true;

  // 127.0.0.0/8 (localhost)
  if (octets[0] === 127) return true;

  return false;
}

/**
 * Get country flag emoji from country code
 */
export function getCountryFlag(countryCode: string): string {
  if (!countryCode || countryCode.length !== 2) return '🏳️';

  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0));

  return String.fromCodePoint(...codePoints);
}

/**
 * Sanitize input to prevent XSS attacks
 */
export function sanitizeInput(input: string): string {
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
}
