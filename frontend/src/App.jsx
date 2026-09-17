import { useEffect, useState } from "react";
import "./styles.css";
import { api } from "./api";
import CourseList from "./components/CourseList";
import UploadView from "./components/UploadView";
import CourseDetail from "./components/CourseDetail";
import DeadlinesView from "./components/DeadlinesView";
import { StampFilterDefs } from "./components/Stamp";

// view = "list" | "upload" | "detail" | "deadlines"
export default function App() {
  const [view, setView] = useState("list");
  const [courses, setCourses] = useState([]);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    refreshCourses();
  }, []);

  async function refreshCourses() {
    setLoadingCourses(true);
    try {
      const data = await api.listCourses();
      setCourses(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingCourses(false);
    }
  }

  async function openCourse(id) {
    setError(null);
    try {
      const course = await api.getCourse(id);
      setSelectedCourse(course);
      setView("detail");
    } catch (err) {
      setError(err.message);
    }
  }

  function handleUploaded(course) {
    setSelectedCourse(course);
    setView("detail");
    refreshCourses();
  }

  async function handleDelete() {
    if (!selectedCourse) return;
    if (!confirm(`Delete ${selectedCourse.course_code || "this course"}? This can't be undone.`)) {
      return;
    }
    await api.deleteCourse(selectedCourse.id);
    setSelectedCourse(null);
    setView("list");
    refreshCourses();
  }

  return (
    <div style={{ minHeight: "100vh" }}>
      <StampFilterDefs />
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "48px 24px 80px" }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 40,
            paddingBottom: 20,
            borderBottom: "1px solid var(--bg-line)",
          }}
        >
          <div style={{ display: "flex", alignItems: "baseline", gap: 24 }}>
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontStyle: "italic",
                fontWeight: 600,
                fontSize: 26,
                letterSpacing: "-0.01em",
                cursor: "pointer",
                color: "var(--paper-text)",
              }}
              onClick={() => setView("list")}
            >
              SyllabusSync
            </div>
            <nav style={{ display: "flex", gap: 4 }}>
              <button
                className="btn-ghost"
                style={{
                  padding: "6px 12px",
                  fontSize: 13,
                  borderRadius: "var(--radius)",
                  border: "none",
                  background: view === "list" ? "var(--bg-raised)" : "transparent",
                  color: view === "list" ? "var(--paper-text)" : "var(--paper-text-muted)",
                }}
                onClick={() => setView("list")}
              >
                Courses
              </button>
              <button
                className="btn-ghost"
                style={{
                  padding: "6px 12px",
                  fontSize: 13,
                  borderRadius: "var(--radius)",
                  border: "none",
                  background: view === "deadlines" ? "var(--bg-raised)" : "transparent",
                  color: view === "deadlines" ? "var(--paper-text)" : "var(--paper-text-muted)",
                }}
                onClick={() => setView("deadlines")}
              >
                Deadlines
              </button>
            </nav>
          </div>
          {view === "list" && courses.length > 0 && (
            <button className="btn" onClick={() => setView("upload")}>
              + Upload syllabus
            </button>
          )}
        </header>

        {error && (
          <div
            className="card"
            style={{
              padding: 14,
              marginBottom: 24,
              background: "var(--stamp-red-soft)",
              color: "var(--stamp-red)",
              fontSize: 13,
              border: "1px solid var(--stamp-red)",
            }}
          >
            {error}
          </div>
        )}

        {view === "list" && (
          <CourseList
            courses={courses}
            loading={loadingCourses}
            onSelectCourse={openCourse}
            onUploadClick={() => setView("upload")}
          />
        )}

        {view === "deadlines" && <DeadlinesView onSelectCourse={openCourse} />}

        {view === "upload" && (
          <UploadView onUploaded={handleUploaded} onCancel={() => setView("list")} />
        )}

        {view === "detail" && selectedCourse && (
          <CourseDetail
            course={selectedCourse}
            onUpdated={setSelectedCourse}
            onBack={() => setView("list")}
            onDelete={handleDelete}
          />
        )}
      </div>
    </div>
  );
}
