import { useCallback, useState } from 'react';
import { Upload, FileText, AlertCircle, Loader2, RotateCcw, CheckCircle2 } from 'lucide-react';
import { cn } from '../lib/utils';

interface SessionInfo {
  fileName: string;
  pageCount: number;
}

interface PDFUploadProps {
  sessionInfo: SessionInfo | null;
  isUploading: boolean;
  uploadError: string | null;
  onUpload: (file: File) => Promise<void>;
  onReset: () => void;
}

export default function PDFUpload({
  sessionInfo,
  isUploading,
  uploadError,
  onUpload,
  onReset,
}: PDFUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setLocalError(null);
      if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
        setLocalError('Please select a PDF file.');
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        setLocalError('File must be under 50 MB.');
        return;
      }
      await onUpload(file);
    },
    [onUpload],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = '';
    },
    [handleFile],
  );

  const error = localError ?? uploadError;

  /* ── Loaded state ── */
  if (sessionInfo) {
    return (
      <div className="space-y-2.5">
        <p className="text-[9px] font-bold uppercase tracking-[0.12em] mb-3" style={{ color: '#5a6492' }}>
          Active Document
        </p>

        {/* File status card */}
        <div
          className="rounded-xl p-3.5 space-y-3"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          {/* Icon + filename */}
          <div className="flex items-start gap-3">
            <div
              className="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
              style={{
                background: 'rgba(79,88,148,0.25)',
                border: '1px solid rgba(79,88,148,0.35)',
              }}
            >
              <FileText className="w-4 h-4" style={{ color: '#8892c0' }} />
            </div>
            <div className="min-w-0 flex-1">
              <p
                className="text-sm font-semibold truncate leading-snug"
                style={{ color: '#c5cee8' }}
                title={sessionInfo.fileName}
              >
                {sessionInfo.fileName}
              </p>
              <p className="text-xs mt-0.5" style={{ color: '#7a84a8' }}>
                {sessionInfo.pageCount} pages
              </p>
            </div>
          </div>

          {/* Status badges */}
          <div className="flex items-center gap-2">
            <div
              className="flex items-center gap-1.5 text-[10px] font-semibold px-2 py-1 rounded"
              style={{ background: 'rgba(90,138,122,0.2)', color: '#7eaaa0' }}
            >
              <CheckCircle2 className="w-3 h-3" />
              Indexed
            </div>
            <div
              className="text-[10px] font-medium px-2 py-1 rounded"
              style={{ background: 'rgba(255,255,255,0.05)', color: '#4a5490' }}
            >
              FAISS ready
            </div>
          </div>
        </div>

        {/* Replace button */}
        <button
          onClick={onReset}
          className="w-full flex items-center justify-center gap-2 text-xs font-medium rounded-lg px-3 py-2.5 transition-all duration-150"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.07)',
            color: '#7a84a8',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.08)';
            (e.currentTarget as HTMLButtonElement).style.color = '#c5cee8';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.03)';
            (e.currentTarget as HTMLButtonElement).style.color = '#7a84a8';
          }}
        >
          <RotateCcw className="w-3 h-3" />
          Replace document
        </button>
      </div>
    );
  }

  /* ── Upload state ── */
  return (
    <div className="space-y-3">
      <p className="text-[9px] font-bold uppercase tracking-[0.12em] mb-3" style={{ color: '#5a6492' }}>
        Document
      </p>

      <label
        className={cn(
          'relative flex flex-col items-center justify-center w-full rounded-xl cursor-pointer transition-all duration-200 py-9 px-5 text-center',
          isUploading && 'pointer-events-none opacity-60',
        )}
        style={{
          background: isDragging ? 'rgba(79,88,148,0.14)' : 'rgba(255,255,255,0.02)',
          border: isDragging
            ? '1.5px dashed rgba(79,88,148,0.55)'
            : '1.5px dashed rgba(255,255,255,0.09)',
          transform: isDragging ? 'scale(1.01)' : 'scale(1)',
        }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".pdf,application/pdf"
          className="sr-only"
          onChange={handleChange}
          disabled={isUploading}
        />

        {isUploading ? (
          <>
            <div
              className="w-11 h-11 rounded-xl flex items-center justify-center mb-3"
              style={{ background: 'rgba(79,88,148,0.18)' }}
            >
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: '#8892c0' }} />
            </div>
            <p className="text-sm font-semibold" style={{ color: '#c5cee8' }}>Processing…</p>
            <p className="text-xs mt-1" style={{ color: '#7a84a8' }}>Extracting · indexing</p>
          </>
        ) : (
          <>
            <div
              className="w-11 h-11 rounded-xl flex items-center justify-center mb-3 transition-colors duration-200"
              style={{
                background: isDragging ? 'rgba(79,88,148,0.22)' : 'rgba(255,255,255,0.04)',
              }}
            >
              {isDragging
                ? <FileText className="w-5 h-5" style={{ color: '#8892c0' }} />
                : <Upload className="w-5 h-5" style={{ color: '#5a6492' }} />
              }
            </div>
            <p className="text-sm font-semibold" style={{ color: isDragging ? '#c5cee8' : '#7a84a8' }}>
              {isDragging ? 'Drop to upload' : 'Drop PDF here'}
            </p>
            <p className="text-xs mt-1" style={{ color: '#4a5490' }}>
              or click to browse · max 50 MB
            </p>
          </>
        )}
      </label>

      {error && (
        <div
          className="flex items-start gap-2 text-xs px-3 py-2.5 rounded-lg"
          style={{
            background: 'rgba(192,80,64,0.14)',
            border: '1px solid rgba(192,80,64,0.28)',
            color: '#e8a898',
          }}
        >
          <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
