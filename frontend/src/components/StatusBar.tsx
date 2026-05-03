import { FileText } from 'lucide-react';

interface StatusBarProps {
  fileName: string;
  pageCount: number;
}

export default function StatusBar({ fileName, pageCount }: StatusBarProps) {
  return (
    <div
      className="shrink-0 h-9 px-6 flex items-center gap-2.5"
      style={{
        background: '#fdf3e0',
        borderTop: '1px solid #e8d8a8',
        borderBottom: '1px solid #e8d8a8',
      }}
    >
      <div
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: '#b07830' }}
      />
      <span className="text-xs" style={{ color: '#8a6c28' }}>
        Answering from
      </span>
      <span className="text-xs font-semibold truncate max-w-xs" style={{ color: '#5c3c08' }}>
        {fileName}
      </span>
      <span
        className="ml-auto shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full"
        style={{ background: '#e8d090', color: '#5c3c08' }}
      >
        {pageCount} pp
      </span>
    </div>
  );
}
