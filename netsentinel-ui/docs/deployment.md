# Netsentinel UI - Deployment Guide

## Netlify Deployment

### Prerequisites
- Netlify account
- GitHub repository access

### Automatic Deployment Setup

1. **Connect Repository to Netlify**
   - Go to [Netlify](https://app.netlify.com/)
   - Click "Add new site" → "Import an existing project"
   - Connect your GitHub repository
   - Netlify will automatically detect the `netlify.toml` configuration

2. **Build Configuration**
   The `netlify.toml` file in the repository root contains:
   ```toml
   [build]
     base = "netsentinel-ui"
     publish = "dist"
     command = "npm run build"

   [build.environment]
     NODE_VERSION = "22"
   ```

3. **Environment Variables**
   Set these environment variables in Netlify:
   ```
   VITE_SENTRY_DSN=your_sentry_dsn_here
   VITE_SENTRY_ENVIRONMENT=production
   ```

4. **Deploy**
   - Netlify will automatically build and deploy on every push to main
   - The build process uses `--legacy-peer-deps` to handle dependency conflicts

### Manual Deployment

If you need to deploy manually:

```bash
# Navigate to the project directory
cd netsentinel-ui

# Install dependencies
npm ci --legacy-peer-deps

# Build for production
npm run build

# Deploy the dist folder to Netlify
# Either drag & drop the dist folder to Netlify dashboard
# Or use Netlify CLI: netlify deploy --prod --dir=dist
```

### Troubleshooting

#### Build Errors
If you encounter build errors:

1. **Dependency Conflicts**: The build script uses `--legacy-peer-deps` to resolve conflicts
2. **Node Version**: Ensure Node.js 22 is selected in Netlify build settings
3. **Build Directory**: Make sure the publish directory is set to `dist`

#### Common Issues

**Vite Plugin Compatibility**
- Updated `@vitejs/plugin-react` to v5+ for Vite 7 compatibility
- Build script includes `npm ci --legacy-peer-deps` to handle peer dependency issues

**React 19 Compatibility**
- All React types updated to support React 19
- Dependencies tested with React 19

### Production Optimizations

The build includes:
- Code splitting with lazy loading
- Vendor chunk separation (React, UI, Charts, Utils)
- Terser minification
- Source maps for error tracking
- Console/debugger removal in production

### Performance Monitoring

The deployed application includes:
- Sentry error tracking
- Performance monitoring dashboard
- Real-time metrics collection
- Automatic error reporting

### SPA Routing

Netlify is configured with SPA fallback:
- All routes redirect to `index.html`
- Client-side routing works correctly
- No 404 errors for direct URL access

### CDN and Assets

- Static assets are served via Netlify's CDN
- Images and fonts are optimized
- Cache headers are automatically set by Netlify

## Alternative Deployment Options

### Vercel

1. Connect repository to Vercel
2. Set build settings:
   - Framework Preset: Vite
   - Root Directory: netsentinel-ui
   - Build Command: npm run build
   - Output Directory: dist

### Other Platforms

For other platforms, ensure:
- Node.js 22+
- Build command: `npm run build`
- Publish directory: `dist`
- SPA redirect rules configured
