import { useState } from "react";
import { api } from "../api";
import Stamp from "./Stamp";

const ASSIGNMENT_TYPES = ["exam", "homework", "project", "quiz", "participation", "other"];

function AssignmentRow({ assignment, courseId, onUpdated }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({
    name: assignment.name,
    type: assignment.type,
    weight_pct: assignment.weight_pct ?? "",
    due_date: assignment.due_date ?? "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const updated = await api.correctAssignment(courseId, assignment.id, {
        name: draft.name,
        type: draft.type,
        weight_pct: draft.weight_pct === "" ? null : parseFloat(draft.weight_pct),
        due_date: draft.due_date === "" ? null : draft.due_date,
      });
      onUpdated(updated);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <tr style={{ background: "var(--card-raised)" }}>
        <td style={{ padding: "10px 12px" }}>
          <input
            type="text"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            style={{ width: "100%" }}
          />
        </td>
        <td style={{ padding: "10px 12px" }}>
          <select value={draft.type} onChange={(e) => setDraft({ ...draft, type: e.target.value })}>
            {ASSIGNMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </td>
        <td style={{ padding: "10px 12px" }}>
          <input
            type="number"
            step="0.1"
            value={draft.weight_pct}
            onChange={(e) => setDraft({ ...draft, weight_pct: e.target.value })}
            style={{ width: 70 }}
          />
        </td>
        <td style={{ padding: "10px 12px" }}>
          <input
            type="date"
            value={draft.due_date}
            onChange={(e) => setDraft({ ...draft, due_date: e.target.value })}
          />
        </td>
        <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>
          <button className="btn" style={{ padding: "5px 12px", fontSize: 12 }} onClick={save} disabled={saving}>
            {saving ? "…" : "Save"}
          </button>
          <button
            className="btn btn-ghost-card"
            style={{ padding: "5px 12px", fontSize: 12, marginLeft: 6 }}
            onClick={() => setEditing(false)}
          >
            Cancel
          </button>
        </td>
      </tr>
    );
  }

  return (
    <tr style={{ borderTop: "1px solid var(--card-line)" }}>
      <td style={{ padding: "12px" }}>{assignment.name}</td>
      <td style={{ padding: "12px", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--card-text-muted)" }}>
        {assignment.type}
      </td>
      <td style={{ padding: "12px", fontFamily: "var(--font-mono)" }}>
        {assignment.weight_pct != null ? `${assignment.weight_pct}%` : "—"}
      </td>
      <td style={{ padding: "12px", fontFamily: "var(--font-mono)", fontSize: 13 }}>
        {assignment.due_date || "—"}
      </td>
      <td style={{ padding: "12px", whiteSpace: "nowrap" }}>
        {assignment.human_corrected && (
          <span className="badge badge-ok" style={{ marginRight: 8 }}>
            Corrected
          </span>
        )}
        {assignment.confidence < 0.7 && !assignment.human_corrected && (
          <span className="badge badge-review" style={{ marginRight: 8 }}>
            Low confidence
          </span>
        )}
        <button
          className="btn btn-ghost-card"
          style={{ padding: "5px 12px", fontSize: 12 }}
          onClick={() => setEditing(true)}
        >
          Edit
        </button>
      </td>
    </tr>
  );
}

function GradeSimulator({ assignments }) {
  const [scores, setScores] = useState({});

  const totalWeight = assignments.reduce((sum, a) => sum + (a.weight_pct || 0), 0);
  const currentGrade = assignments.reduce((sum, a) => {
    const score = scores[a.id];
    if (score === undefined || score === "" || !a.weight_pct) return sum;
    return sum + (parseFloat(score) / 100) * a.weight_pct;
  }, 0);

  const enteredWeight = assignments.reduce((sum, a) => {
    const score = scores[a.id];
    if (score === undefined || score === "") return sum;
    return sum + (a.weight_pct || 0);
  }, 0);

  return (
    <div className="card" style={{ padding: 24, marginTop: 20 }}>
      <p style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 19, margin: "0 0 4px" }}>
        Grade simulator
      </p>
      <p style={{ color: "var(--card-text-muted)", fontSize: 13, marginBottom: 18 }}>
        Enter a score for any assignment to see how it affects your total.
      </p>

      <div style={{ display: "grid", gap: 10 }}>
        {assignments.map((a) => (
          <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ flex: 1, fontSize: 14 }}>
              {a.name}{" "}
              <span style={{ color: "var(--card-text-muted)", fontSize: 12, fontFamily: "var(--font-mono)" }}>
                ({a.weight_pct ?? "?"}%)
              </span>
            </span>
            <input
              type="number"
              placeholder="score %"
              min="0"
              max="100"
              value={scores[a.id] ?? ""}
              onChange={(e) => setScores({ ...scores, [a.id]: e.target.value })}
              style={{ width: 92 }}
            />
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 18,
          paddingTop: 18,
          borderTop: "1px solid var(--card-line)",
          fontFamily: "var(--font-mono)",
          fontSize: 14,
        }}
      >
        Current weighted grade:{" "}
        <strong style={{ fontSize: 16 }}>{currentGrade.toFixed(1)}%</strong>{" "}
        <span style={{ color: "var(--card-text-muted)", fontSize: 12 }}>
          (based on {enteredWeight}% of {totalWeight}% total weight entered)
        </span>
      </div>
    </div>
  );
}

export default function CourseDetail({ course, onUpdated, onBack, onDelete }) {
  function handleAssignmentUpdated(updated) {
    onUpdated({
      ...course,
      assignments: course.assignments.map((a) => (a.id === updated.id ? updated : a)),
    });
  }

  return (
    <div>
      <button className="btn btn-ghost" style={{ marginBottom: 20 }} onClick={onBack}>
        ← All courses
      </button>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
        <div>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: 32,
              margin: "0 0 4px",
              color: "var(--paper-text)",
            }}
          >
            {course.course_code || "Untitled course"}
          </h1>
          {course.course_name && (
            <p style={{ color: "var(--paper-text-muted)", margin: 0, fontSize: 16 }}>
              {course.course_name}
            </p>
          )}
          {course.instructor && (
            <p
              style={{
                color: "var(--paper-text-muted)",
                fontSize: 13,
                margin: "6px 0 0",
                fontFamily: "var(--font-mono)",
              }}
            >
              {course.instructor} {course.term && `· ${course.term}`}
            </p>
          )}
        </div>
        <button className="btn btn-danger" onClick={onDelete}>
          Delete course
        </button>
      </div>

      {course.needs_review && (
        <div
          className="card"
          style={{
            marginTop: 20,
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            gap: 18,
            borderColor: "var(--stamp-red)",
          }}
        >
          <Stamp label="Needs review" variant="review" animate />
          <p style={{ margin: 0, fontSize: 13, color: "var(--card-text)", lineHeight: 1.5 }}>
            Extraction flagged this syllabus for review. Check the assignments
            below for anything missing or wrong before trusting the deadlines.
          </p>
        </div>
      )}

      <div className="card" style={{ marginTop: 24, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "var(--card-raised)", textAlign: "left" }}>
              <th style={{ padding: "12px", fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--card-text-muted)" }}>Assignment</th>
              <th style={{ padding: "12px", fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--card-text-muted)" }}>Type</th>
              <th style={{ padding: "12px", fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--card-text-muted)" }}>Weight</th>
              <th style={{ padding: "12px", fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--card-text-muted)" }}>Due date</th>
              <th style={{ padding: "12px" }}></th>
            </tr>
          </thead>
          <tbody>
            {course.assignments.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: 28, textAlign: "center", color: "var(--card-text-muted)" }}>
                  Nothing was extracted from this syllabus. Manually adding
                  assignments isn't supported yet — try re-uploading a clearer file.
                </td>
              </tr>
            ) : (
              course.assignments.map((a) => (
                <AssignmentRow
                  key={a.id}
                  assignment={a}
                  courseId={course.id}
                  onUpdated={handleAssignmentUpdated}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {course.assignments.length > 0 && <GradeSimulator assignments={course.assignments} />}
    </div>
  );
}
