export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  created_at: string;
  document_count: number;
}

export interface Document {
  id: string;
  kb_id: string;
  source_type: "text" | "pdf" | "image" | "audio";
  filename: string;
  title: string | null;
  status: "uploading" | "processing" | "ready" | "failed";
  version: number;
  file_size: number | null;
  mime_type: string | null;
  created_at: string;
}

export interface Citation {
  id: string;
  content: string;
  chunk_index: number;
  metadata: Record<string, unknown>;
  filename: string;
  source_type: string;
  similarity: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export interface Conversation {
  id: string;
  kb_id: string;
  title: string;
  created_at: string;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  cited_chunk_ids: string[];
  created_at: string;
}
