import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import fs from 'fs';
import uploadRouter from './routes/upload';
import chatRouter from './routes/chat';

dotenv.config();

const app = express();
const PORT = parseInt(process.env.PORT || '3001', 10);

const uploadDir = process.env.UPLOAD_DIR || './uploads';
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

app.use(
  cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:5173',
    credentials: true,
  }),
);
app.use(express.json({ limit: '10mb' }));

app.use('/api/upload', uploadRouter);
app.use('/api/chat', chatRouter);

app.get('/api/health', (_, res) => {
  res.json({ status: 'ok', provider: process.env.LLM_PROVIDER || 'openai' });
});

app.listen(PORT, () => {
  console.log(`PDF Chat backend → http://localhost:${PORT}`);
  console.log(`LLM provider    → ${process.env.LLM_PROVIDER || 'openai'}`);
});
