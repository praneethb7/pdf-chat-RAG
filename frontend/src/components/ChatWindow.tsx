import type { RefObject } from 'react';
import { BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Message } from '../types';
import ChatMessage from './ChatMessage';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  hasSession: boolean;
  messagesEndRef: RefObject<HTMLDivElement>;
}

export default function ChatWindow({ messages, isLoading, hasSession, messagesEndRef }: ChatWindowProps) {
  if (!hasSession) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-10 bg-canvas select-none">
        <div
          className="w-14 h-14 rounded-2xl flex items-center justify-center mb-5"
          style={{
            background: 'linear-gradient(135deg, #f0ebe2 0%, #e8e2d8 100%)',
            border: '1px solid #ddd6c8',
          }}
        >
          <BookOpen className="w-6 h-6" style={{ color: '#b0a898' }} />
        </div>
        <h2 className="text-[17px] font-semibold tracking-tight" style={{ color: '#1e1b2e' }}>
          Ask something about your document
        </h2>
        <p className="text-sm mt-2 max-w-sm leading-relaxed" style={{ color: '#7a7898' }}>
          Upload a PDF from the panel on the left. Every answer will be grounded directly in the text you provide.
        </p>
        <div
          className="mt-7 flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-lg"
          style={{
            background: '#f0ebe2',
            border: '1px solid #ddd6c8',
            color: '#7a7898',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M8 6H1M1 6L4 3M1 6L4 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Drop a PDF in the sidebar to begin
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-canvas bg-canvas">
      <div className="max-w-2xl mx-auto px-6 py-8 space-y-7">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
            >
              <ChatMessage message={msg} />
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="flex items-start gap-3"
          >
            <AiAvatar />
            <div
              className="px-4 py-3 rounded-xl rounded-tl-sm"
              style={{
                background: '#ffffff',
                border: '1px solid #e8e2d8',
                boxShadow: '0 1px 3px rgba(30,27,46,0.06)',
              }}
            >
              <div className="flex items-center gap-1.5">
                <span className="text-xs mr-1" style={{ color: '#aeacbe' }}>Thinking</span>
                <span className="w-1.5 h-1.5 rounded-full bg-ink-faint animate-dot-1" />
                <span className="w-1.5 h-1.5 rounded-full bg-ink-faint animate-dot-2" />
                <span className="w-1.5 h-1.5 rounded-full bg-ink-faint animate-dot-3" />
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}

export function AiAvatar({ size = 'md' }: { size?: 'sm' | 'md' }) {
  const dim = size === 'sm' ? 'w-7 h-7' : 'w-8 h-8';
  return (
    <div
      className={`${dim} rounded-lg flex items-center justify-center shrink-0 mt-0.5`}
      style={{
        background: 'linear-gradient(135deg, #3a4278 0%, #4f5894 100%)',
        boxShadow: '0 2px 6px rgba(30,27,46,0.2)',
      }}
    >
      <span className="text-white text-[8px] font-bold tracking-widest">AI</span>
    </div>
  );
}
