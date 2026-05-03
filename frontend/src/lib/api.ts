import type { ChatResponse, UploadResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadPDF(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('pdf', file);
  return request<UploadResponse>('/api/upload', { method: 'POST', body: formData });
}

export async function sendMessage(
  sessionId: string,
  question: string,
): Promise<ChatResponse> {
  return request<ChatResponse>('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, question }),
  });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await request(`/api/chat/session/${sessionId}`, { method: 'DELETE' });
}
