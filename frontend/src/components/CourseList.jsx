export default function CourseList({ courses, onSelectCourse, onUploadClick, loading }) {
  if (loading) {
    return <p style={{ color: "var(--ink-soft)" }}>Loading courses…</p>;
  }

  if (courses.length === 0) {
    return (
      <div className="card" style={{ padding: 40, textAlign: "center" }}>
        <p style={{ fontFamily: "var(--font-display)", fontSize: 20, margin: "0 0 8px" }}>
          No courses yet
        </p>
        <p style={{ color: "var(--ink-soft)", marginBottom: 20 }}>
          Upload a syllabus PDF to pull out deadlines and grading weights automatically.
        </p>
        <button className="btn" onClick={onUploadClick}>
          Upload a syllabus
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {courses.map((course) => (
        <div
          key={course.id}
          className="card"
          style={{
            padding: 20,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            cursor: "pointer",
          }}
          onClick={() => onSelectCourse(course.id)}
        >
          <div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 19 }}>
              {course.course_code || "Untitled course"}
              {course.course_name && (
                <span style={{ color: "var(--ink-soft)", fontWeight: 400 }}>
                  {" — "}
                  {course.course_name}
                </span>
              )}
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-soft)", marginTop: 4 }}>
              {course.term || "Term not detected"} · weights sum to {course.total_weight_pct}%
            </div>
          </div>
          {course.needs_review && <span className="badge badge-review">Needs review</span>}
        </div>
      ))}
    </div>
  );
}
