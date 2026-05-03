import { useState } from 'react';
import { AlertTriangle, ChevronRight, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Message } from '../types';
import { cn } from '../lib/utils';
import CitationBlock from './CitationBlock';
import { AiAvatar } from './ChatWindow';

export default function ChatMessage({ message }: { message: Message }) {
  const isUser       = message.role === 'user';
  const hasCitations = !message.isOutOfScope && (message.citations?.length ?? 0) > 0;
  const [showWhy, setShowWhy] = useState(false);

  return (
    <div className={cn('flex items-start gap-3', isUser && 'flex-row-reverse')}>
      {/* ── Avatar ── */}
      {isUser ? (
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
          style={{
            background: 'linear-gradient(135deg, #3a4278 0%, #4f5894 100%)',
            boxShadow: '0 2px 6px rgba(30,27,46,0.22)',
          }}
        >
          <span className="text-white text-[8px] font-bold tracking-widest">YOU</span>
        </div>
      ) : (
        <AiAvatar />
      )}

      {/* ── Content column ── */}
      <div className={cn('max-w-[80%] space-y-1.5', isUser && 'flex flex-col items-end')}>

        {/* User bubble */}
        {isUser && (
          <div
            className="px-4 py-3 rounded-2xl rounded-tr-sm text-sm leading-relaxed"
            style={{
              background: 'linear-gradient(135deg, #3a4278 0%, #4f5894 100%)',
              boxShadow: '0 3px 10px rgba(79,88,148,0.35), 0 1px 3px rgba(79,88,148,0.18)',
              color: '#ffffff',
            }}
          >
            <p className="whitespace-pre-wrap font-medium">{message.content}</p>
          </div>
        )}

        {/* Out-of-scope card */}
        {!isUser && message.isOutOfScope && (
          <div
            className="rounded-xl rounded-tl-sm text-sm leading-relaxed overflow-hidden"
            style={{ background: '#fdf0ee', border: '1px solid #e8a898' }}
          >
            <div
              className="flex items-center gap-2 px-4 py-2.5 text-[11px] font-semibold"
              style={{ background: '#f8ddd8', borderBottom: '1px solid #e8a898', color: '#8c2a1a' }}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Outside document scope
            </div>
            <p className="px-4 py-3.5 whitespace-pre-wrap" style={{ color: '#42405a' }}>
              {message.content}
            </p>
          </div>
        )}

        {/* Normal assistant structured card */}
        {!isUser && !message.isOutOfScope && (
          <>
            <div
              className="rounded-xl rounded-tl-sm overflow-hidden"
              style={{
                background: '#ffffff',
                border: '1px solid #e8e2d8',
                boxShadow: '0 1px 3px rgba(30,27,46,0.06), 0 2px 8px rgba(30,27,46,0.04)',
              }}
            >
              {/* Answer section */}
              <div className="px-5 py-4">
                <p className="text-sm whitespace-pre-wrap" style={{ color: '#1e1b2e', lineHeight: '1.75' }}>
                  {message.content}
                </p>
              </div>

              {/* Citation section — separated by ruled line */}
              {hasCitations && (
                <>
                  <div style={{ borderTop: '1px solid #f0ebe2', margin: '0 20px' }} />
                  <div className="px-5 py-4">
                    <CitationBlock citations={message.citations!} />
                  </div>
                </>
              )}
            </div>

            {/* "Why this answer?" — observability toggle */}
            {hasCitations && (
              <div className="pl-1 space-y-1.5">
                <button
                  onClick={() => setShowWhy((v) => !v)}
                  className="flex items-center gap-1.5 text-xs transition-colors duration-150"
                  style={{ color: showWhy ? '#4f5894' : '#aeacbe' }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.color = '#4f5894';
                  }}
                  onMouseLeave={(e) => {
                    if (!showWhy) (e.currentTarget as HTMLButtonElement).style.color = '#aeacbe';
                  }}
                >
                  <ChevronRight
                    className="w-3 h-3 transition-transform duration-150"
                    style={{ transform: showWhy ? 'rotate(90deg)' : 'rotate(0deg)' }}
                  />
                  <Cpu className="w-3 h-3" />
                  Why this answer?
                </button>

                <AnimatePresence>
                  {showWhy && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2, ease: 'easeOut' }}
                      className="overflow-hidden"
                    >
                      <div
                        className="rounded-lg px-4 py-3 text-xs space-y-1.5"
                        style={{
                          background: '#f5f3ff',
                          border: '1px solid #dde0f8',
                          color: '#5a5880',
                        }}
                      >
                        <div className="font-semibold text-[11px] mb-2" style={{ color: '#4f5894' }}>
                          RAG trace
                        </div>
                        <div>
                          Retrieved{' '}
                          <span className="font-semibold">{message.citations!.length}</span>{' '}
                          passage{message.citations!.length !== 1 ? 's' : ''} from your document
                        </div>
                        <div>
                          Pages referenced:{' '}
                          <span className="font-semibold">
                            {[...new Set(message.citations!.map((c) => c.page))]
                              .sort((a, b) => a - b)
                              .join(', ')}
                          </span>
                        </div>
                        <div
                          className="text-[10px] pt-1.5 mt-0.5"
                          style={{ borderTop: '1px solid #dde0f8', color: '#8892c0' }}
                        >
                          Answer grounded exclusively in uploaded document · FAISS similarity search
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </>
        )}

        {/* Timestamp */}
        <p
          className={cn('text-[10px] font-medium', isUser ? 'text-right' : 'text-left')}
          style={{ color: '#aeacbe' }}
        >
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}
