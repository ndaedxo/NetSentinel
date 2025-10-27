## Netsentinel

Enterprise-grade AI-powered network security platform with honeypot detection, threat intelligence, and automated response capabilities.

## Setup

### Environment Variables

1. **Copy the environment template:**
   ```bash
   cp .env-example .env
   ```

2. **Configure your environment variables:**
   Update `.env` with your actual values for authentication, database, and other services.

### Development Setup

The application currently runs without authentication enabled for UI development. To add authentication:

1. Implement your own authentication system in `src/worker/index.ts`
2. Update the auth endpoints (`/api/users/me`, `/api/sessions`, etc.)
3. Re-enable authentication components in `src/App.tsx` and `src/components/Header.tsx`

**Note:** Authentication is currently disabled to allow for UI development and testing.

## Running the Application

To run the devserver:
```
npm install
npm run dev
```
