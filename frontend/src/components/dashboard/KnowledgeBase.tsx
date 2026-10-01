"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  Upload, FileText, Trash2,
  Search, CheckCircle, Loader, BookOpen, Zap, AlertCircle, RefreshCw,
} from "lucide-react";
import {
  fetchKnowledgeDocs,
  uploadKnowledgeDoc,
  deleteKnowledgeDoc,
  type KnowledgeDoc,
  fmtBytes,
} from "@/lib/api";

const typeColor: Record<string, string> = {
  pdf: "#ef4444", csv: "#22d3a0", txt: "#f59e0b", docx: "#4f6eff",
};

const statusStyle: Record<string, { label: string; cls: string }> = {
  indexed:    { label: "Indexed",    cls: "badge-green" },
  processing: { label: "Processing", cls: "badge-blue"  },
  pending:    { label: "Pending",    cls: "badge-amber" },
  failed:     { label: "Failed",     cls: "badge-red"   },
};

export default function KnowledgeBase() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [search, setSearch] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocs = useCallback(async () => {
    try {
      const data = await fetchKnowledgeDocs();
      setDocs(data);
      setError(null);
    } catch {
      setError("Backend not reachable — showing local state only.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll every 5s while any doc is processing/pending (to detect when indexing finishes)
  useEffect(() => {
    loadDocs();
    const t = setInterval(() => {
      const hasProcessing = docs.some(
        (d) => d.status === "processing" || d.status === "pending"
      );
      if (hasProcessing) loadDocs();
    }, 5_000);
    return () => clearInterval(t);
  }, [loadDocs, docs]);

  const filtered = docs.filter(
    (d) =>
      d.title.toLowerCase().includes(search.toLowerCase()) ||
      (d.file_name ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const totalChunks  = docs.reduce((s, d) => s + (d.chunk_count ?? 0), 0);
  const indexedCount = docs.filter((d) => d.status === "indexed").length;
  const processingCnt = docs.filter(
    (d) => d.status === "processing" || d.status === "pending"
  ).length;

  const handleFiles = useCallback(
    async (files: File[]) => {
      if (!files.length) return;
      setUploading(true);
      setError(null);
      try {
        for (const file of files) {
          const title = file.name.replace(/\.[^.]+$/, ""); // strip extension
          const created = await uploadKnowledgeDoc(file, title);
          setDocs((prev) => [
            {
              ...created,
              file_name: file.name,
              file_size_bytes: file.size,
              chunk_count: null,
              error: null,
            },
            ...prev,
          ]);
        }
        // Start polling for status updates
        setTimeout(loadDocs, 2_000);
      } catch (e) {
        setError(
          "Upload failed. Make sure the backend is running at http://localhost:8000."
        );
      } finally {
        setUploading(false);
      }
    },
    [loadDocs]
  );

  const handleDelete = useCallback(async (docId: string) => {
    // Optimistic remove
    setDocs((prev) => prev.filter((d) => d.id !== docId));
    try {
      await deleteKnowledgeDoc(docId);
    } catch {
      // Re-load if delete failed
      loadDocs();
    }
  }, [loadDocs]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      handleFiles(Array.from(e.dataTransfer.files));
    },
    [handleFiles]
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Knowledge Base</h2>
          <p className="text-xs mt-0.5" style={{ color: "rgba(226,232,240,0.4)" }}>
            Upload documents — AI searches them semantically on every call (pgvector RAG)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadDocs}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all"
            style={{
              background: "rgba(79,110,255,0.08)",
              color: "#6b8fff",
              border: "1px solid rgba(79,110,255,0.15)",
            }}
          >
            <RefreshCw size={11} /> Refresh
          </button>
          <button
            id="knowledge-upload-btn"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold"
            style={{
              background: "linear-gradient(135deg,#4f6eff,#22d3a0)",
              color: "#fff",
              boxShadow: "0 0 20px rgba(79,110,255,0.3)",
            }}
          >
            <Upload size={14} /> Upload Document
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.csv,.txt,.docx"
            className="hidden"
            onChange={(e) => handleFiles(Array.from(e.target.files || []))}
          />
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl text-xs"
          style={{
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            color: "#ef4444",
          }}
        >
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Documents",     value: docs.length,                       color: "#4f6eff", Icon: BookOpen    },
          { label: "Indexed",       value: indexedCount,                      color: "#22d3a0", Icon: CheckCircle },
          { label: "Processing",    value: processingCnt,                     color: "#f59e0b", Icon: Loader      },
          { label: "Vector Chunks", value: totalChunks.toLocaleString("en-IN"), color: "#a855f7", Icon: Zap       },
        ].map(({ label, value, color, Icon }) => (
          <div key={label} className="glass-card stat-card p-4">
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ background: `${color}18` }}
              >
                <Icon size={15} style={{ color }} />
              </div>
              <div>
                <p className="text-xl font-bold text-white">{value}</p>
                <p className="text-xs" style={{ color: "rgba(226,232,240,0.45)" }}>
                  {label}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Drop zone + document list */}
      <div className="grid grid-cols-3 gap-6">
        {/* Drop zone */}
        <div
          id="knowledge-dropzone"
          className="col-span-1 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-200 p-8"
          style={{
            borderColor: dragOver ? "rgba(79,110,255,0.8)" : "rgba(107,143,255,0.2)",
            background:  dragOver ? "rgba(79,110,255,0.07)" : "rgba(13,20,40,0.4)",
            minHeight: 220,
          }}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <div className="text-center">
              <Loader
                size={28}
                style={{
                  color: "#4f6eff",
                  margin: "0 auto 8px",
                  animation: "spin 1s linear infinite",
                }}
              />
              <p className="text-sm" style={{ color: "#4f6eff" }}>Uploading...</p>
              <p className="text-xs mt-1" style={{ color: "rgba(226,232,240,0.4)" }}>
                Starting RAG ingestion
              </p>
            </div>
          ) : (
            <>
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
                style={{ background: "rgba(79,110,255,0.12)" }}
              >
                <Upload size={24} style={{ color: "#4f6eff" }} />
              </div>
              <p className="text-sm font-semibold text-white mb-1">Drop files here</p>
              <p className="text-xs text-center" style={{ color: "rgba(226,232,240,0.4)" }}>
                PDF, CSV, DOCX, TXT
              </p>
              <div
                className="mt-4 px-4 py-1.5 rounded-full text-xs font-semibold"
                style={{
                  background: "rgba(79,110,255,0.15)",
                  color: "#4f6eff",
                  border: "1px solid rgba(79,110,255,0.3)",
                }}
              >
                Browse files
              </div>
              <p className="text-xs mt-4 text-center" style={{ color: "rgba(226,232,240,0.25)" }}>
                AI will index and search these during every call
              </p>
            </>
          )}
        </div>

        {/* Document list */}
        <div className="col-span-2 space-y-3">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: "rgba(226,232,240,0.4)" }}
            />
            <input
              id="knowledge-search"
              type="text"
              placeholder="Search documents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm outline-none"
              style={{
                background: "rgba(13,20,40,0.7)",
                border: "1px solid rgba(107,143,255,0.15)",
                color: "#e2e8f0",
              }}
            />
          </div>

          <div
            className="glass-card divide-y"
            style={{
              borderColor: "rgba(255,255,255,0.04)",
              maxHeight: 360,
              overflowY: "auto",
            }}
          >
            {loading ? (
              <div className="p-8 text-center" style={{ color: "rgba(226,232,240,0.4)" }}>
                Loading documents...
              </div>
            ) : filtered.length === 0 ? (
              <div className="p-8 text-center" style={{ color: "rgba(226,232,240,0.35)" }}>
                {docs.length === 0
                  ? "No documents yet. Upload a PDF or CSV to get started."
                  : "No documents matching your search."}
              </div>
            ) : (
              filtered.map((doc) => {
                const ss = statusStyle[doc.status] ?? statusStyle.pending;
                const color = typeColor[doc.file_type] ?? "#888";
                return (
                  <div
                    key={doc.id}
                    id={`doc-${doc.id}`}
                    className="flex items-center gap-4 p-4"
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ background: `${color}18` }}
                    >
                      <FileText size={15} style={{ color }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-sm font-medium text-white truncate">{doc.title}</p>
                        <span
                          className={`badge ${ss.cls}`}
                          style={{ fontSize: "0.6rem", flexShrink: 0 }}
                        >
                          {ss.label}
                        </span>
                      </div>
                      <p
                        className="text-xs truncate"
                        style={{ color: "rgba(226,232,240,0.45)" }}
                      >
                        {doc.file_name ?? "—"}
                        {doc.error && (
                          <span className="ml-2" style={{ color: "#ef4444" }}>
                            ⚠ {doc.error}
                          </span>
                        )}
                      </p>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="text-xs" style={{ color: "rgba(226,232,240,0.4)" }}>
                        {fmtBytes(doc.file_size_bytes)}
                      </p>
                      {(doc.chunk_count ?? 0) > 0 && (
                        <p
                          className="text-xs font-mono"
                          style={{ color: "#a855f7" }}
                        >
                          {doc.chunk_count} chunks
                        </p>
                      )}
                      <p
                        className="text-xs"
                        style={{ color: "rgba(226,232,240,0.25)" }}
                      >
                        {doc.created_at.slice(0, 10)}
                      </p>
                    </div>
                    <button
                      id={`delete-doc-${doc.id}`}
                      onClick={() => handleDelete(doc.id)}
                      className="p-1.5 rounded-lg transition-all hover:bg-red-500/10"
                      style={{ color: "rgba(239,68,68,0.5)" }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* RAG info bar */}
      <div
        className="glass-card p-4 flex items-center gap-4"
        style={{
          borderColor: "rgba(168,85,247,0.2)",
          background: "rgba(168,85,247,0.04)",
        }}
      >
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: "rgba(168,85,247,0.15)" }}
        >
          <Zap size={16} style={{ color: "#a855f7" }} />
        </div>
        <div className="flex-1">
          <p className="text-xs font-semibold text-white">Semantic Search Active</p>
          <p className="text-xs" style={{ color: "rgba(226,232,240,0.45)" }}>
            {totalChunks.toLocaleString("en-IN")} vector embeddings · pgvector · Top-K=5 · Cosine similarity · Gemini re-ranking
          </p>
        </div>
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full"
          style={{
            background: indexedCount > 0
              ? "rgba(34,211,160,0.1)"
              : "rgba(226,232,240,0.05)",
            border: `1px solid ${indexedCount > 0 ? "rgba(34,211,160,0.3)" : "rgba(226,232,240,0.1)"}`,
          }}
        >
          {indexedCount > 0 && <span className="live-dot-inner" />}
          <span
            className="text-xs font-semibold"
            style={{ color: indexedCount > 0 ? "#22d3a0" : "rgba(226,232,240,0.4)" }}
          >
            {indexedCount > 0 ? "RAG ONLINE" : "NO DOCS INDEXED"}
          </span>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}