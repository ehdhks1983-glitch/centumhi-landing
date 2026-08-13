import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import generateRouter from './routes/generate.js';
import analyzeRouter from './routes/analyze.js';
import historyRouter from './routes/history.js';
import usageRouter from './routes/usage.js';

const app = express();
const PORT = process.env.PORT || 3000;

// ─── Middleware ───────────────────────────────────────────
const allowedOrigins = process.env.ALLOWED_ORIGINS
  ? process.env.ALLOWED_ORIGINS.split(',').map(s => s.trim())
  : true; // allow all origins in dev

app.use(cors({
  origin: allowedOrigins,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

app.use(express.json({ limit: '10mb' }));

app.use((req, res, next) => {
  res.on('finish', () => {
    console.log(`${req.method} ${req.path} → ${res.statusCode}`);
  });
  next();
});

// ─── Routes ───────────────────────────────────────────────
app.use('/api/generate', generateRouter);
app.use('/api/analyze-place', analyzeRouter);
app.use('/api/generate-content', generateRouter); // spec alias
app.use('/api/history', historyRouter);
app.use('/api/save-generation', historyRouter);
app.use('/api/usage', usageRouter);

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', ts: new Date().toISOString() });
});

// ─── Error handler ────────────────────────────────────────
app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(err.status || 500).json({
    message: err.message || '서버 오류가 발생했습니다',
  });
});

app.listen(PORT, () => {
  console.log(`✅ 사장님 콘텐츠비서 API  →  http://localhost:${PORT}`);
});
