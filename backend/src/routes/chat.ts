import { Router, Request, Response } from 'express';
import { queryPDF, deleteSession, getSessionInfo } from '../services/ragService';

const router = Router();

router.post('/', async (req: Request, res: Response): Promise<void> => {
  const { sessionId, question } = req.body as { sessionId?: string; question?: string };

  if (!sessionId || typeof sessionId !== 'string') {
    res.status(400).json({ error: 'sessionId is required' });
    return;
  }
  if (!question || typeof question !== 'string' || !question.trim()) {
    res.status(400).json({ error: 'question must be a non-empty string' });
    return;
  }
  if (question.trim().length > 2000) {
    res.status(400).json({ error: 'Question exceeds 2000 character limit' });
    return;
  }

  try {
    const result = await queryPDF(sessionId, question.trim());
    res.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to process question';
    res.status(message.includes('not found') ? 404 : 500).json({ error: message });
  }
});

router.get('/session/:sessionId', (req: Request, res: Response): void => {
  const info = getSessionInfo(req.params.sessionId);
  if (!info) {
    res.status(404).json({ error: 'Session not found' });
    return;
  }
  res.json(info);
});

router.delete('/session/:sessionId', (req: Request, res: Response): void => {
  const deleted = deleteSession(req.params.sessionId);
  if (!deleted) {
    res.status(404).json({ error: 'Session not found' });
    return;
  }
  res.json({ message: 'Session deleted' });
});

export default router;
