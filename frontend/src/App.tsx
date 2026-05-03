import { useState, useRef, useEffect, useCallback } from 'react';
import { BookOpen } from 'lucide-react';
import { uploadPDF, sendMessage, deleteSession } from './lib/api';
import type { Message, UploadResponse } from './types';
import PDFUpload from './components/PDFUpload';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import StatusBar from './components/StatusBar';

interface Session {
  id: string;
  fileName: string;
  pageCount: number;
}

export default function App() {
  const [session, setSession]         = useState<Session | null>(null);
  const [messages, setMessages]       = useState<Message[]>([]);
  const [isLoading, setIsLoading]     = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleUpload = useCallback(async (file: File) => {
    setIsUploading(true);
    setUploadError(null);
    try {
      const result: UploadResponse = await uploadPDF(file);
      setSession({ id: result.sessionId, fileName: result.fileName, pageCount: result.pageCount });
      setMessages([{
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `I've read "${result.fileName}" (${result.pageCount} pages). What would you like to know?`,
        timestamp: new Date(),
      }]);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleSend = useCallback(async (question: string) => {
    if (!session || isLoading) return;
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: question, timestamp: new Date() },
    ]);
    setIsLoading(true);
    try {
      const result = await sendMessage(session.id, question);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: result.answer,
          citations: result.citations,
          isOutOfScope: result.isOutOfScope,
          timestamp: new Date(),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
          isOutOfScope: true,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [session, isLoading]);

  const handleReset = useCallback(async () => {
    if (session) await deleteSession(session.id).catch(() => {});
    setSession(null);
    setMessages([]);
    setUploadError(null);
  }, [session]);

  return (
    <div className="flex h-full overflow-hidden" style={{ background: '#f9f6f1' }}>

      {/* ── Sidebar ── deep slate-indigo panel */}
      <aside
        className="w-[272px] shrink-0 flex flex-col"
        style={{
          background: '#171a2e',
          boxShadow: '4px 0 32px rgba(0,0,0,0.24)',
        }}
      >
        {/* Wordmark strip */}
        <div
          className="px-5 py-4 flex items-center gap-3 shrink-0"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{
              background: 'linear-gradient(135deg, #3a4278 0%, #4f5894 100%)',
              boxShadow: '0 2px 8px rgba(30,27,46,0.45)',
            }}
          >
            <BookOpen className="w-4 h-4 text-white" strokeWidth={2} />
          </div>
          <div className="leading-tight">
            <h1 className="text-[13px] font-semibold tracking-tight" style={{ color: '#c5cee8' }}>
              PDF Chat
            </h1>
            <p className="text-[11px] mt-0.5" style={{ color: '#4a5490' }}>
              Document intelligence
            </p>
          </div>
        </div>

        {/* PDF context panel */}
        <div className="flex-1 p-4 overflow-y-auto scrollbar-panel">
          <PDFUpload
            sessionInfo={session ? { fileName: session.fileName, pageCount: session.pageCount } : null}
            isUploading={isUploading}
            uploadError={uploadError}
            onUpload={handleUpload}
            onReset={handleReset}
          />
        </div>

        {/* Footer note */}
        <div
          className="px-4 py-3 shrink-0"
          style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
        >
          <p className="text-[10px] leading-relaxed" style={{ color: '#343c6a' }}>
            Answers grounded strictly in the uploaded document. Out-of-scope questions are flagged.
          </p>
        </div>
      </aside>

      {/* ── Chat column ── */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          hasSession={!!session}
          messagesEndRef={messagesEndRef}
        />

        {/* Context indicator bar — only when a document is loaded */}
        {session && (
          <StatusBar fileName={session.fileName} pageCount={session.pageCount} />
        )}

        {/* Input area */}
        <div
          className="shrink-0 px-6 py-4"
          style={{ background: '#f9f6f1' }}
        >
          <div className="max-w-2xl mx-auto">
            <ChatInput
              onSend={handleSend}
              isLoading={isLoading}
              disabled={!session}
              placeholder={
                session
                  ? 'Ask about this document… (Enter to send, Shift+Enter for new line)'
                  : 'Upload a PDF to start chatting'
              }
            />
            {!session && (
              <p className="text-center text-xs mt-2" style={{ color: '#aeacbe' }}>
                All answers come exclusively from your uploaded document
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
