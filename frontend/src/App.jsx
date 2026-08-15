import { useEffect, useState } from "react";
import "./styles.css";
import { api } from "./api";
import CourseList from "./components/CourseList";
import UploadView from "./components/UploadView";
import CourseDetail from "./components/CourseDetail";

// view = "list" | "upload" | "detail"
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
    <div style={{ maxWidth: 780, margin: "0 auto", padding: "40px 24px" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div style={{ fontFamily: "var(--font-display)", fontSize: 22, cursor: "pointer" }} onClick={() => setView("list")}>
          SyllabusSync
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
            padding: 12,
            marginBottom: 20,
            background: "var(--coral-soft)",
            color: "var(--coral)",
            fontSize: 13,
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
  );
}
