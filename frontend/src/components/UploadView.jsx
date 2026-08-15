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
    <div className="card" style={{ padding: 32, maxWidth: 480 }}>
      <p style={{ fontFamily: "var(--font-display)", fontSize: 20, margin: "0 0 4px" }}>
        Upload a syllabus
      </p>
      <p style={{ color: "var(--ink-soft)", fontSize: 14, marginBottom: 20 }}>
        PDF or Word (.docx, .dotx). Extraction runs automatically — you'll be able to
        fix anything it gets wrong on the next screen.
      </p>

      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept="application/pdf,.docx,.dotx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.wordprocessingml.template"
          onChange={(e) => setFile(e.target.files[0])}
          style={{ marginBottom: 16, fontFamily: "var(--font-mono)", fontSize: 13 }}
        />

        {error && (
          <p style={{ color: "var(--coral)", fontSize: 13, marginBottom: 12 }}>{error}</p>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" className="btn" disabled={!file || loading}>
            {loading ? "Extracting…" : "Upload"}
          </button>
          <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={loading}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
