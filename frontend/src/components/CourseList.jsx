import Stamp from "./Stamp";

export default function CourseList({ courses, onSelectCourse, onUploadClick, loading }) {
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
    <div style={{ display: "grid", gap: 14 }}>
      {courses.map((course) => (
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
  );
}
