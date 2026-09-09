import { useMemo, useState } from "react";
import Stamp from "./Stamp";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "review", label: "Needs review" },
  { key: "verified", label: "Verified" },
];

function matchesFilter(course, filterKey) {
  if (filterKey === "review") return course.needs_review;
  if (filterKey === "verified") return !course.needs_review && course.total_weight_pct > 0;
  return true;
}

function matchesQuery(course, query) {
  if (!query.trim()) return true;
  const haystack = [course.course_code, course.course_name, course.term]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(query.trim().toLowerCase());
}

export default function CourseList({ courses, onSelectCourse, onUploadClick, loading }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");

  const filteredCourses = useMemo(
    () => courses.filter((c) => matchesFilter(c, filter) && matchesQuery(c, query)),
    [courses, filter, query]
  );

  if (loading) {
    return <p style={{ color: "var(--paper-text-muted)" }}>Loading courses…</p>;
  }

  if (courses.length === 0) {
    return (
      <div className="card" style={{ padding: 48, textAlign: "center" }}>
        <p
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 24,
            margin: "0 0 8px",
            fontWeight: 600,
          }}
        >
          Nothing filed yet
        </p>
        <p style={{ color: "var(--card-text-muted)", marginBottom: 24, maxWidth: 380, marginInline: "auto" }}>
          Upload a syllabus and SyllabusSync will pull out deadlines, grading
          weights, and due dates automatically.
        </p>
        <button className="btn" onClick={onUploadClick}>
          Upload a syllabus
        </button>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 18, alignItems: "center", flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Search courses…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ flex: "1 1 220px", minWidth: 180 }}
        />
        <div style={{ display: "flex", gap: 4 }}>
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              style={{
                padding: "6px 12px",
                fontSize: 12,
                fontFamily: "var(--font-mono)",
                borderRadius: "var(--radius)",
                border: "1px solid var(--bg-line)",
                background: filter === f.key ? "var(--bg-raised)" : "transparent",
                color: filter === f.key ? "var(--paper-text)" : "var(--paper-text-muted)",
                cursor: "pointer",
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {filteredCourses.length === 0 ? (
        <div className="card" style={{ padding: 32, textAlign: "center", color: "var(--card-text-muted)" }}>
          No courses match{query.trim() ? ` "${query.trim()}"` : " this filter"}.
        </div>
      ) : (
        <div style={{ display: "grid", gap: 14 }}>
          {filteredCourses.map((course) => (
            <div
              key={course.id}
              className="card card-hover"
              style={{
                padding: "22px 24px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                cursor: "pointer",
              }}
              onClick={() => onSelectCourse(course.id)}
            >
              <div>
                <div style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 20 }}>
                  {course.course_code || "Untitled course"}
                  {course.course_name && (
                    <span style={{ color: "var(--card-text-muted)", fontWeight: 400 }}>
                      {" — "}
                      {course.course_name}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                    color: "var(--card-text-muted)",
                    marginTop: 6,
                    letterSpacing: "0.01em",
                  }}
                >
                  {course.term || "Term not detected"} · weights sum to {course.total_weight_pct}%
                </div>
              </div>
              {course.needs_review && <Stamp label="Needs review" variant="review" />}
              {!course.needs_review && course.total_weight_pct > 0 && (
                <Stamp label="Verified" variant="verified" />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
