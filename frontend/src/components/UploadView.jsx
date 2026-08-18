import { useState } from "react";
import { api } from "../api";

export default function UploadView({ onUploaded, onCancel }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const course = await api.uploadSyllabus(file);
      onUploaded(course);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ padding: 36, maxWidth: 480 }}>
      <p
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 600,
          fontSize: 22,
          margin: "0 0 6px",
        }}
      >
        Upload a syllabus
      </p>
      <p style={{ color: "var(--card-text-muted)", fontSize: 14, marginBottom: 22, lineHeight: 1.5 }}>
        PDF or Word (.docx, .dotx). Extraction runs automatically — you'll be able to
        fix anything it gets wrong on the next screen.
      </p>

      <form onSubmit={handleSubmit}>
        <div
          style={{
            border: `1px dashed var(--card-line)`,
            borderRadius: "var(--radius)",
            padding: 20,
            marginBottom: 18,
            background: "var(--card-raised)",
          }}
        >
          <input
            type="file"
            accept="application/pdf,.docx,.dotx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.wordprocessingml.template"
            onChange={(e) => setFile(e.target.files[0])}
            style={{ fontFamily: "var(--font-mono)", fontSize: 13, width: "100%" }}
          />
        </div>

        {error && (
          <p
            style={{
              color: "var(--stamp-red)",
              fontSize: 13,
              marginBottom: 14,
              padding: "8px 12px",
              background: "var(--stamp-red-soft)",
              borderRadius: "var(--radius)",
            }}
          >
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: 10 }}>
          <button type="submit" className="btn" disabled={!file || loading}>
            {loading ? "Extracting…" : "Upload"}
          </button>
          <button type="button" className="btn btn-ghost-card" onClick={onCancel} disabled={loading}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
