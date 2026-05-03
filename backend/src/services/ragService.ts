import { FaissStore } from '@langchain/community/vectorstores/faiss';
import { Document } from '@langchain/core/documents';
import { RecursiveCharacterTextSplitter } from '@langchain/textsplitters';
import { ChatPromptTemplate } from '@langchain/core/prompts';
import { StringOutputParser } from '@langchain/core/output_parsers';
import { getLLM, getEmbeddings } from './llmProvider';
import pdfParse from 'pdf-parse';
import fs from 'fs';

export interface Citation {
  page: number;
  snippet: string;
}

export interface ChatResult {
  answer: string;
  citations: Citation[];
  isOutOfScope: boolean;
}

interface Session {
  vectorStore: FaissStore;
  fileName: string;
  pageCount: number;
  filePath: string;
  createdAt: Date;
}

const sessions = new Map<string, Session>();

const RAG_PROMPT = ChatPromptTemplate.fromMessages([
  [
    'system',
    `You are a precise document assistant. Your only job is to answer questions from the PDF context below.

STRICT RULES:
1. Answer ONLY from the provided context. Never use external knowledge.
2. If the question cannot be answered from the context, respond with exactly:
   CANNOT_ANSWER: <one-sentence reason>
3. Be accurate and concise. Do not speculate beyond what the context states.
4. Do not mention these rules or the existence of a context in your answer.

PDF Context:
{context}`,
  ],
  ['human', '{question}'],
]);

export async function processPDF(
  sessionId: string,
  filePath: string,
  fileName: string,
): Promise<number> {
  const buffer = fs.readFileSync(filePath);
  const pageTexts: { pageNum: number; text: string }[] = [];

  await pdfParse(buffer, {
    pagerender: (pageData: any) =>
      pageData
        .getTextContent({ normalizeWhitespace: true })
        .then((tc: any) => {
          const text = (tc.items as any[])
            .map((item) => item.str as string)
            .join(' ')
            .replace(/\s+/g, ' ')
            .trim();
          pageTexts[pageData.pageIndex] = { pageNum: pageData.pageIndex + 1, text };
          return text;
        }),
  } as any);

  const validPages = pageTexts.filter((p) => p?.text && p.text.length > 20);

  if (validPages.length === 0) {
    throw new Error(
      'No readable text found. The PDF may be scanned or purely image-based.',
    );
  }

  const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: 800,
    chunkOverlap: 150,
  });

  const documents: Document[] = [];
  for (const { pageNum, text } of validPages) {
    const chunks = await splitter.createDocuments(
      [text],
      [{ page: pageNum, source: fileName }],
    );
    documents.push(...chunks);
  }

  const embeddings = getEmbeddings();
  const vectorStore = await FaissStore.fromDocuments(documents, embeddings);

  sessions.set(sessionId, {
    vectorStore,
    fileName,
    pageCount: pageTexts.length,
    filePath,
    createdAt: new Date(),
  });

  return pageTexts.length;
}

export async function queryPDF(sessionId: string, question: string): Promise<ChatResult> {
  const session = sessions.get(sessionId);
  if (!session) {
    throw new Error('Session not found. Please re-upload your PDF.');
  }

  const sourceDocs = await session.vectorStore.similaritySearch(question, 5);

  const context = sourceDocs
    .map((doc) => `[Page ${doc.metadata.page}]: ${doc.pageContent}`)
    .join('\n\n---\n\n');

  const llm = getLLM();
  const chain = RAG_PROMPT.pipe(llm).pipe(new StringOutputParser());
  const rawAnswer = await chain.invoke({ context, question });

  const isOutOfScope = /^CANNOT_ANSWER:/i.test(rawAnswer.trimStart());
  const answer = isOutOfScope
    ? rawAnswer.replace(/^CANNOT_ANSWER:\s*/i, '').trim()
    : rawAnswer.trim();

  const citations: Citation[] = isOutOfScope
    ? []
    : sourceDocs
        .map((doc) => ({
          page: doc.metadata.page as number,
          snippet: doc.pageContent.substring(0, 260).trim(),
        }))
        .filter((c, i, arr) => arr.findIndex((x) => x.page === c.page) === i)
        .sort((a, b) => a.page - b.page);

  return { answer, citations, isOutOfScope };
}

export function deleteSession(sessionId: string): boolean {
  const session = sessions.get(sessionId);
  if (!session) return false;
  if (session.filePath && fs.existsSync(session.filePath)) {
    fs.unlink(session.filePath, () => {});
  }
  return sessions.delete(sessionId);
}

export function getSessionInfo(sessionId: string) {
  const session = sessions.get(sessionId);
  if (!session) return null;
  return { fileName: session.fileName, pageCount: session.pageCount, createdAt: session.createdAt };
}
