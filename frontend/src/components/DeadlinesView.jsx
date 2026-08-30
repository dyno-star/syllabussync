import { useEffect, useState } from "react";
import { api } from "../api";

function daysUntil(dueDateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDateStr + "T00:00:00");
  const diffMs = due - today;
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

function urgencyLabel(days) {
  if (days < 0) return { text: "Overdue", tone: "review" };
  if (days === 0) return { text: "Due today", tone: "review" };
  if (days <= 3) return { text: `${days} day${days === 1 ? "" : "s"} left`, tone: "review" };
  if (days <= 7) return { text: `${days} days left`, tone: "ok" };
  return { text: `${days} days left`, tone: null };
}

export default function DeadlinesView({ onSelectCourse }) {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getUpcomingAssignments()
      .then(setAssignments)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p style={{ color: "var(--paper-text-muted)" }}>Loading deadlines…</p>;
  }

  if (error) {
    return (
      <div
        className="card"
        style={{ padding: 14, background: "var(--stamp-red-soft)", color: "var(--stamp-red)" }}
      >
        {error}
      </div>
    );
  }

  if (assignments.length === 0) {
    return (
      <div className="card" style={{ padding: 48, textAlign: "center" }}>
        <p style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 600, margin: "0 0 8px" }}>
          Nothing on the calendar
        </p>
        <p style={{ color: "var(--card-text-muted)", margin: 0 }}>
          Assignments with a due date will show up here, across all your courses.
        </p>
      </div>
    );
  }

  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "var(--card-raised)", textAlign: "left" }}>
            <th style={headerCellStyle}>Due</th>
            <th style={headerCellStyle}>Assignment</th>
            <th style={headerCellStyle}>Course</th>
            <th style={headerCellStyle}>Weight</th>
            <th style={headerCellStyle}></th>
          </tr>
        </thead>
        <tbody>
          {assignments.map((a) => {
            const days = daysUntil(a.due_date);
            const urgency = urgencyLabel(days);
            return (
              <tr
                key={a.assignment_id}
                style={{ borderTop: "1px solid var(--card-line)", cursor: "pointer" }}
                onClick={() => onSelectCourse(a.course_id)}
              >
                <td style={{ padding: "12px", fontFamily: "var(--font-mono)", fontSize: 13, whiteSpace: "nowrap" }}>
                  {a.due_date}
                </td>
                <td style={{ padding: "12px" }}>{a.name}</td>
                <td style={{ padding: "12px", color: "var(--card-text-muted)" }}>
                  {a.course_code || "Untitled"}
                </td>
                <td style={{ padding: "12px", fontFamily: "var(--font-mono)" }}>
                  {a.weight_pct != null ? `${a.weight_pct}%` : "—"}
                </td>
                <td style={{ padding: "12px" }}>
                  {urgency.tone && (
                    <span className={`badge badge-${urgency.tone}`}>{urgency.text}</span>
                  )}
                  {!urgency.tone && (
                    <span style={{ fontSize: 12, color: "var(--card-text-muted)", fontFamily: "var(--font-mono)" }}>
                      {urgency.text}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const headerCellStyle = {
  padding: "12px",
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  letterSpacing: "0.05em",
  textTransform: "uppercase",
  color: "var(--card-text-muted)",
};
