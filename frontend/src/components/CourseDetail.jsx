import { useState } from "react";
import { api } from "../api";

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
      <tr>
        <td>
          <input
            type="text"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            style={{ width: "100%" }}
          />
        </td>
        <td>
          <select value={draft.type} onChange={(e) => setDraft({ ...draft, type: e.target.value })}>
            {ASSIGNMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </td>
        <td>
          <input
            type="number"
            step="0.1"
            value={draft.weight_pct}
            onChange={(e) => setDraft({ ...draft, weight_pct: e.target.value })}
            style={{ width: 70 }}
          />
        </td>
        <td>
          <input
            type="date"
            value={draft.due_date}
            onChange={(e) => setDraft({ ...draft, due_date: e.target.value })}
          />
        </td>
        <td>
          <button className="btn" style={{ padding: "4px 10px", fontSize: 12 }} onClick={save} disabled={saving}>
            {saving ? "…" : "Save"}
          </button>
          <button
            className="btn btn-ghost"
            style={{ padding: "4px 10px", fontSize: 12, marginLeft: 6 }}
            onClick={() => setEditing(false)}
          >
            Cancel
          </button>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>{assignment.name}</td>
      <td style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-soft)" }}>
        {assignment.type}
      </td>
      <td style={{ fontFamily: "var(--font-mono)" }}>
        {assignment.weight_pct != null ? `${assignment.weight_pct}%` : "—"}
      </td>
      <td style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}>
        {assignment.due_date || "—"}
      </td>
      <td>
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
          className="btn btn-ghost"
          style={{ padding: "4px 10px", fontSize: 12 }}
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
    <div className="card" style={{ padding: 20, marginTop: 24 }}>
      <p style={{ fontFamily: "var(--font-display)", fontSize: 17, margin: "0 0 4px" }}>
        Grade simulator
      </p>
      <p style={{ color: "var(--ink-soft)", fontSize: 13, marginBottom: 16 }}>
        Enter a score for any assignment to see how it affects your total.
      </p>

      <div style={{ display: "grid", gap: 8 }}>
        {assignments.map((a) => (
          <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ flex: 1, fontSize: 14 }}>
              {a.name} <span style={{ color: "var(--ink-soft)", fontSize: 12 }}>({a.weight_pct ?? "?"}%)</span>
            </span>
            <input
              type="number"
              placeholder="score %"
              min="0"
              max="100"
              value={scores[a.id] ?? ""}
              onChange={(e) => setScores({ ...scores, [a.id]: e.target.value })}
              style={{ width: 90 }}
            />
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 16,
          paddingTop: 16,
          borderTop: "1px solid var(--line)",
          fontFamily: "var(--font-mono)",
          fontSize: 14,
        }}
      >
        Current weighted grade: <strong>{currentGrade.toFixed(1)}%</strong>{" "}
        <span style={{ color: "var(--ink-soft)", fontSize: 12 }}>
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
      <button className="btn btn-ghost" style={{ marginBottom: 16 }} onClick={onBack}>
        ← All courses
      </button>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 28, margin: "0 0 4px" }}>
            {course.course_code || "Untitled course"}
          </h1>
          {course.course_name && (
            <p style={{ color: "var(--ink-soft)", margin: 0 }}>{course.course_name}</p>
          )}
          {course.instructor && (
            <p style={{ color: "var(--ink-soft)", fontSize: 13, margin: "4px 0 0" }}>
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
            marginTop: 16,
            padding: 12,
            background: "var(--coral-soft)",
            border: "1px solid var(--coral)",
            fontSize: 13,
            color: "var(--coral)",
          }}
        >
          Extraction flagged this syllabus for review. Check the assignments below
          for anything missing or wrong before trusting the deadlines.
        </div>
      )}

      <div className="card" style={{ marginTop: 20, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "var(--paper)", textAlign: "left" }}>
              <th style={{ padding: "10px 12px" }}>Assignment</th>
              <th style={{ padding: "10px 12px" }}>Type</th>
              <th style={{ padding: "10px 12px" }}>Weight</th>
              <th style={{ padding: "10px 12px" }}>Due date</th>
              <th style={{ padding: "10px 12px" }}></th>
            </tr>
          </thead>
          <tbody>
            {course.assignments.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: 20, textAlign: "center", color: "var(--ink-soft)" }}>
                  Nothing was extracted from this syllabus. Add assignments manually
                  isn't supported yet — try re-uploading a clearer PDF.
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
