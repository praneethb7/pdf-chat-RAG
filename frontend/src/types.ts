export interface Citation {
  page: number;
  snippet: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isOutOfScope?: boolean;
  timestamp: Date;
}

export interface UploadResponse {
  sessionId: string;
  fileName: string;
  pageCount: number;
  message: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  isOutOfScope: boolean;
}
