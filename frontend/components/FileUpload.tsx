"use client";
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, Loader2, FileText } from "lucide-react";
import { api } from "@/lib/api";

interface FileUploadProps {
  kbId: string;
  onUploadComplete: () => void;
}

export function FileUpload({ kbId, onUploadComplete }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [uploads, setUploads] = useState<{ name: string; status: "uploading" | "processing" | "done" | "error" }[]>([]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const newUploads = acceptedFiles.map((f) => ({ name: f.name, status: "uploading" as const }));
      setUploads((prev) => [...prev, ...newUploads]);

      for (let i = 0; i < acceptedFiles.length; i++) {
        const file = acceptedFiles[i];
        const idx = uploads.length + i;
        setUploading(true);
        try {
          setUploads((prev) => prev.map((u, j) => (j === idx ? { ...u, status: "processing" } : u)));
          await api.uploadDocument(kbId, file);
          setUploads((prev) => prev.map((u, j) => (j === idx ? { ...u, status: "done" } : u)));
        } catch {
          setUploads((prev) => prev.map((u, j) => (j === idx ? { ...u, status: "error" } : u)));
        }
        setUploading(false);
      }
      onUploadComplete();
    },
    [kbId, onUploadComplete, uploads.length]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, disabled: uploading });

  return (
    <div className="space-y-2">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all
          ${isDragActive
            ? "border-indigo-400 bg-indigo-50"
            : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
          }
          ${uploading ? "opacity-50 pointer-events-none" : ""}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            Processing...
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <Upload className="w-5 h-5 text-gray-400" />
            <p className="text-xs text-gray-500">Drop files or click</p>
            <p className="text-[10px] text-gray-400">PDF, TXT, images, audio</p>
          </div>
        )}
      </div>

      {uploads.map((u, i) => (
        <div key={i} className="flex items-center gap-2 px-2 py-1.5 bg-gray-100 rounded text-xs">
          <FileText className="w-3 h-3 text-gray-400 shrink-0" />
          <span className="truncate text-gray-700">{u.name}</span>
          {u.status === "processing" && <Loader2 className="w-3 h-3 animate-spin text-indigo-500 ml-auto shrink-0" />}
          {u.status === "done" && <span className="text-green-500 ml-auto shrink-0">Done</span>}
          {u.status === "error" && <span className="text-red-500 ml-auto shrink-0">Failed</span>}
        </div>
      ))}
    </div>
  );
}
