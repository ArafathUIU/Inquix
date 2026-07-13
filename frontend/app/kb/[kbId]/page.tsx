"use client";
import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Brain, ArrowLeft, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { FileUpload } from "@/components/FileUpload";
import { DocumentList } from "@/components/DocumentList";
import { ChatInterface } from "@/components/ChatInterface";
import type { KnowledgeBase, Document as Doc } from "@/types";

export default function KBPage() {
  const params = useParams();
  const router = useRouter();
  const kbId = params.kbId as string;

  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [sidebarTab, setSidebarTab] = useState<"docs" | "convs">("docs");

  const loadData = useCallback(async () => {
    try {
      const [kbData, docsData] = await Promise.all([
        api.getKB(kbId),
        api.listDocuments(kbId),
      ]);
      setKb(kbData);
      setDocuments(docsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [kbId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUploadComplete = () => {
    loadData();
  };

  const handleDeleteDocument = async (docId: string) => {
    await api.deleteDocument(kbId, docId);
    loadData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!kb) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500">Knowledge base not found.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-600" />
            <h1 className="font-semibold text-gray-900">{kb.name}</h1>
          </div>
          <span className="text-xs text-gray-400 ml-1">{documents.length} docs</span>
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-80 border-r border-gray-200 bg-gray-50/50 flex flex-col shrink-0">
          <div className="p-3">
            <FileUpload kbId={kbId} onUploadComplete={handleUploadComplete} />
          </div>
          <div className="flex-1 overflow-y-auto px-3 pb-3">
            <DocumentList
              documents={documents}
              onDelete={handleDeleteDocument}
            />
          </div>
        </aside>

        {/* Chat area */}
        <main className="flex-1 flex flex-col">
          <ChatInterface kbId={kbId} />
        </main>
      </div>
    </div>
  );
}
