"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Brain, Plus, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { KnowledgeBase } from "@/types";

export default function HomePage() {
  const router = useRouter();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    api.listKBs().then(setKbs).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const kb = await api.createKB(newName.trim());
      router.push(`/kb/${kb.id}`);
    } catch (e) {
      console.error(e);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    await api.deleteKB(id);
    setKbs((prev) => prev.filter((k) => k.id !== id));
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600 mb-4">
            <Brain className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Inquix</h1>
          <p className="text-gray-500 mt-1">Multi-modal RAG — upload documents and ask questions</p>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : kbs.length === 0 ? (
          <div className="space-y-4">
            <div className="text-center py-8 text-gray-400">
              <p>No knowledge bases yet.</p>
              <p className="text-sm">Create one to get started.</p>
            </div>
            {showCreate ? (
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Knowledge base name..."
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowCreate(false)}
                    className="flex-1 px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreate}
                    disabled={creating || !newName.trim()}
                    className="flex-1 px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {creating ? "Creating..." : "Create"}
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowCreate(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Create Knowledge Base
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {kbs.map((kb) => (
              <div
                key={kb.id}
                onClick={() => router.push(`/kb/${kb.id}`)}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg cursor-pointer hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors"
              >
                <div>
                  <h3 className="font-medium text-gray-900">{kb.name}</h3>
                  <p className="text-xs text-gray-500">{kb.document_count} documents</p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(kb.id);
                  }}
                  className="p-1.5 text-gray-400 hover:text-red-500 rounded transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              onClick={() => setShowCreate(true)}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Knowledge Base
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
