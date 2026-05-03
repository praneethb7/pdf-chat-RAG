import { ChatOpenAI, OpenAIEmbeddings } from '@langchain/openai';
import { ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings } from '@langchain/google-genai';
import type { BaseChatModel } from '@langchain/core/language_models/chat_models';
import type { Embeddings } from '@langchain/core/embeddings';

type Provider = 'openai' | 'gemini';

function getProvider(): Provider {
  const p = (process.env.LLM_PROVIDER || 'openai').toLowerCase();
  if (p !== 'openai' && p !== 'gemini') {
    throw new Error(`Unsupported LLM_PROVIDER "${p}". Use "openai" or "gemini".`);
  }
  return p;
}

export function getLLM(): BaseChatModel {
  const provider = getProvider();

  if (provider === 'gemini') {
    if (!process.env.GEMINI_API_KEY) throw new Error('GEMINI_API_KEY is required');
    return new ChatGoogleGenerativeAI({
      model: 'gemini-1.5-flash',
      apiKey: process.env.GEMINI_API_KEY,
      temperature: 0,
    });
  }

  if (!process.env.OPENAI_API_KEY) throw new Error('OPENAI_API_KEY is required');
  return new ChatOpenAI({
    model: 'gpt-4o-mini',
    apiKey: process.env.OPENAI_API_KEY,
    temperature: 0,
  });
}

export function getEmbeddings(): Embeddings {
  const provider = getProvider();

  if (provider === 'gemini') {
    if (!process.env.GEMINI_API_KEY) throw new Error('GEMINI_API_KEY is required');
    return new GoogleGenerativeAIEmbeddings({
      model: 'embedding-001',
      apiKey: process.env.GEMINI_API_KEY,
    });
  }

  if (!process.env.OPENAI_API_KEY) throw new Error('OPENAI_API_KEY is required');
  return new OpenAIEmbeddings({
    model: 'text-embedding-3-small',
    apiKey: process.env.OPENAI_API_KEY,
  });
}
