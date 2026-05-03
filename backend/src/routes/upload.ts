import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import { processPDF } from '../services/ragService';

const router = Router();

const uploadDir = process.env.UPLOAD_DIR || './uploads';
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });

const storage = multer.diskStorage({
  destination: uploadDir,
  filename: (_, file, cb) => {
    const id = uuidv4();
    const ext = path.extname(file.originalname).toLowerCase() || '.pdf';
    cb(null, `${id}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: {
    fileSize: parseInt(process.env.MAX_FILE_SIZE_MB || '50', 10) * 1024 * 1024,
  },
  fileFilter: (_, file, cb) => {
    const ok =
      file.mimetype === 'application/pdf' ||
      path.extname(file.originalname).toLowerCase() === '.pdf';
    ok ? cb(null, true) : cb(new Error('Only PDF files are accepted'));
  },
});

router.post(
  '/',
  upload.single('pdf'),
  async (req: Request, res: Response): Promise<void> => {
    if (!req.file) {
      res.status(400).json({ error: 'No PDF file provided' });
      return;
    }

    const sessionId = path.basename(req.file.filename, path.extname(req.file.filename));

    try {
      const pageCount = await processPDF(sessionId, req.file.path, req.file.originalname);
      res.json({
        sessionId,
        fileName: req.file.originalname,
        pageCount,
        message: `Processed ${pageCount} pages successfully.`,
      });
    } catch (err) {
      fs.unlink(req.file.path, () => {});
      const message = err instanceof Error ? err.message : 'Failed to process PDF';
      res.status(500).json({ error: message });
    }
  },
);

export default router;
