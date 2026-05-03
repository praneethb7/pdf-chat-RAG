import { useState } from 'react';
import { BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Citation } from '../types';

export default function CitationBlock({ citations }: { citations: Citation[] }) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const toggle = (idx: number) => setOpenIdx((prev) => (prev === idx ? null : idx));

  return (
    <div className="space-y-3">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <BookOpen className="w-3.5 h-3.5 shrink-0" style={{ color: '#b07830' }} />
        <span
          className="text-[10px] font-bold uppercase tracking-[0.1em]"
          style={{ color: '#8a6420' }}
        >
          Sources
        </span>
        <span
          className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
          style={{ background: '#e8d090', color: '#5c3c08' }}
        >
          {citations.length}
        </span>
      </div>

      {/* Citation rows */}
      <div className="space-y-1.5">
        {citations.map((citation, i) => (
          <div key={i}>
            <button
              onClick={() => toggle(i)}
              className="w-full flex items-center gap-2.5 text-left group"
            >
              {/* Page badge — fills solid when expanded */}
              <span
                className="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded transition-colors duration-150"
                style={{
                  background: openIdx === i ? '#b07830' : '#e8d090',
                  color: openIdx === i ? '#ffffff' : '#6c4610',
                }}
              >
                p.{citation.page}
              </span>

              {/* Truncated snippet preview */}
              <span
                className="text-xs flex-1 truncate transition-colors duration-150"
                style={{ color: openIdx === i ? '#42405a' : '#7a7898' }}
              >
                {citation.snippet.slice(0, 70)}{citation.snippet.length > 70 ? '…' : ''}
              </span>

              {/* Chevron */}
              <span
                className="shrink-0 text-[9px] transition-all duration-150"
                style={{
                  color: openIdx === i ? '#b07830' : '#aeacbe',
                  transform: openIdx === i ? 'rotate(90deg)' : 'rotate(0deg)',
                  display: 'inline-block',
                }}
              >
                ›
              </span>
            </button>

            <AnimatePresence>
              {openIdx === i && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.18, ease: 'easeOut' }}
                  className="overflow-hidden"
                >
                  <div
                    className="mt-2 px-3.5 py-2.5 rounded-lg text-xs leading-relaxed italic"
                    style={{
                      background: '#fdf3e0',
                      border: '1px solid #e8d090',
                      borderLeft: '3px solid #b07830',
                      color: '#5a4828',
                    }}
                  >
                    &ldquo;{citation.snippet}&rdquo;
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </div>
  );
}
