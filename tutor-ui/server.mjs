// Minimal static server for the built SPA (Railway "frontend" service).
// Serves dist/ and falls back to index.html for client-side (react-router) routes.
import express from 'express';
import helmet from 'helmet';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.join(__dirname, 'dist');
const port = process.env.PORT || 8080;

const app = express();

// Configure helmet with CSP that allows API connections
const apiUrl = process.env.VITE_API_URL || 'https://adaptive-genai-learning-tutor-production.up.railway.app';
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      connectSrc: ["'self'", apiUrl, "https://*.railway.app"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      fontSrc: ["'self'", "https:", "data:"],
    },
  },
}));

// Hashed asset files can be cached aggressively; index.html is revalidated.
app.use(
  express.static(distDir, {
    index: false,
    setHeaders: (res, filePath) => {
      if (filePath.endsWith('index.html')) res.setHeader('Cache-Control', 'no-cache');
      else if (filePath.includes(`${path.sep}assets${path.sep}`)) res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
    },
  }),
);

// Simple liveness endpoint for the platform.
app.get('/healthz', (_req, res) => res.json({ ok: true }));

// SPA fallback — every other route serves index.html so deep links work.
app.get('*', (_req, res) => {
  res.sendFile(path.join(distDir, 'index.html'));
});

app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`tutor-ui static server listening on :${port}`);
});
