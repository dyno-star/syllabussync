const BASE = "/api";

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  uploadSyllabus(file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${BASE}/documents/upload`, { method: "POST", body: formData }).then(handle);
  },

  listCourses() {
    return fetch(`${BASE}/courses/`).then(handle);
  },

  getCourse(id) {
    return fetch(`${BASE}/courses/${id}`).then(handle);
  },

  updateCourse(id, update) {
    return fetch(`${BASE}/courses/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }).then(handle);
  },

  deleteCourse(id) {
    return fetch(`${BASE}/courses/${id}`, { method: "DELETE" }).then(handle);
  },

  correctAssignment(courseId, assignmentId, update) {
    return fetch(`${BASE}/courses/${courseId}/assignments/${assignmentId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }).then(handle);
  },
};
