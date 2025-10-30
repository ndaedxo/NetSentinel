/**
 * Mock implementation of @faker-js/faker for testing
 */

// Simple deterministic random number generator for consistent test results
class SimpleRNG {
  private seed: number;

  constructor(seed: number = 12345) {
    this.seed = seed;
  }

  next(): number {
    this.seed = (this.seed * 9301 + 49297) % 233280;
    return this.seed / 233280;
  }

  int(min: number, max: number): number {
    return Math.floor(this.next() * (max - min + 1)) + min;
  }

  float(min: number = 0, max: number = 1): number {
    return this.next() * (max - min) + min;
  }

  arrayElement<T>(array: T[]): T {
    return array[this.int(0, array.length - 1)];
  }

  words(count: number = 3): string {
    const words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua'];
    return Array.from({ length: count }, () => this.arrayElement(words)).join(' ');
  }

  sentence(): string {
    return this.words(this.int(5, 15)) + '.';
  }
}

// Global RNG instance
let globalRNG = new SimpleRNG();

// Map to store seeded RNG instances
const seededRNGs = new Map<number, SimpleRNG>();

// Mock faker object
const mockFaker = {
  seed: (value: number) => {
    if (!seededRNGs.has(value)) {
      seededRNGs.set(value, new SimpleRNG(value));
    }
    globalRNG = seededRNGs.get(value)!;
  },

  datatype: {
    boolean: () => globalRNG.next() > 0.5,
  },

  number: {
    int: ({ min, max }: { min: number; max: number }) => globalRNG.int(min, max),
    float: ({ min = 0, max = 1 }: { min?: number; max?: number }) => globalRNG.float(min, max),
  },

  internet: {
    ip: () => `192.168.${globalRNG.int(0, 255)}.${globalRNG.int(0, 255)}`,
    mac: () => {
      const mac: string[] = [];
      for (let i = 0; i < 6; i++) {
        mac.push(globalRNG.int(0, 255).toString(16).padStart(2, '0'));
      }
      return mac.join(':');
    },
  },

  lorem: {
    words: (count?: number) => globalRNG.words(count),
    sentence: () => globalRNG.sentence(),
  },

  helpers: {
    arrayElement: <T>(array: T[]) => globalRNG.arrayElement(array),
    arrayElements: <T>(array: T[], options: { min?: number; max?: number } = {}) => {
      const { min = 1, max = array.length } = options;
      const count = globalRNG.int(min, Math.min(max, array.length));
      const result: T[] = [];
      const available = [...array];

      for (let i = 0; i < count && available.length > 0; i++) {
        const index = globalRNG.int(0, available.length - 1);
        result.push(available.splice(index, 1)[0]);
      }

      return result;
    },
  },

      string: {
        alphanumeric: (length: number = 8) => {
          const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
          return Array.from({ length }, () =>
            chars.charAt(Math.floor(Math.random() * chars.length))
          ).join('');
        },
        uuid: () => {
          const template = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
          return template.replace(/[xy]/g, (c) => {
            const r = globalRNG.int(0, 15);
            const v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
          });
        }
      },

  person: {
    firstName: () => globalRNG.arrayElement(['John', 'Jane', 'Bob', 'Alice', 'Mike', 'Sarah', 'David', 'Emma', 'Chris', 'Lisa']),
    lastName: () => globalRNG.arrayElement(['Smith', 'Johnson', 'Brown', 'Williams', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']),
    fullName: () => `${globalRNG.arrayElement(['John', 'Jane', 'Bob', 'Alice'])} ${globalRNG.arrayElement(['Smith', 'Johnson', 'Brown', 'Williams'])}`
  },

  company: {
    buzzNoun: () => globalRNG.arrayElement(['Security', 'Network', 'Data', 'System', 'Cloud', 'Analytics', 'Monitoring', 'Intelligence']),
    name: () => `${globalRNG.arrayElement(['Tech', 'Cyber', 'Net', 'Data'])} ${globalRNG.arrayElement(['Solutions', 'Systems', 'Corp', 'Inc'])}`
  },

  date: {
    recent: (options?: { days?: number } | number) => {
      const now = new Date();
      const days = typeof options === 'number' ? options : (options?.days || 7);
      const randomDays = globalRNG.int(0, days);
      return new Date(now.getTime() - randomDays * 24 * 60 * 60 * 1000);
    },
  },
};

export { mockFaker as faker };
export default mockFaker;

