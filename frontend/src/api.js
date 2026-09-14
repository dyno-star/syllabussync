const BASE = "/api";
const TOKEN_KEY = "syllabussync_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle(res) {
  if (res.status === 401) {
    // Token missing/invalid/expired — clear it so the app falls back to
    // the login screen on next render, rather than looping on 401s.
    clearToken();
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  isAuthenticated() {
    return !!getToken();
  },

  logout() {
    clearToken();
  },

  async register(email, password) {
    const res = await fetch(`${BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await handle(res);
    setToken(data.access_token);
    return data;
  },

  async login(email, password) {
    const res = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await handle(res);
    setToken(data.access_token);
    return data;
  },

  getMe() {
    return fetch(`${BASE}/auth/me`, { headers: authHeaders() }).then(handle);
  },

  uploadSyllabus(file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${BASE}/documents/upload`, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    }).then(handle);
  },

  listCourses() {
    return fetch(`${BASE}/courses/`, { headers: authHeaders() }).then(handle);
  },

  getCourse(id) {
    return fetch(`${BASE}/courses/${id}`, { headers: authHeaders() }).then(handle);
  },

  getUpcomingAssignments() {
    return fetch(`${BASE}/courses/upcoming`, { headers: authHeaders() }).then(handle);
  },

  updateCourse(id, update) {
    return fetch(`${BASE}/courses/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(update),
    }).then(handle);
  },

  deleteCourse(id) {
    return fetch(`${BASE}/courses/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    }).then(handle);
  },

  correctAssignment(courseId, assignmentId, update) {
    return fetch(`${BASE}/courses/${courseId}/assignments/${assignmentId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(update),
    }).then(handle);
  },

  recordAssignmentScore(courseId, assignmentId, scorePct) {
    return fetch(`${BASE}/courses/${courseId}/assignments/${assignmentId}/score`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ score_pct: scorePct }),
    }).then(handle);
  },

  createAssignment(courseId, newAssignment) {
    return fetch(`${BASE}/courses/${courseId}/assignments`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(newAssignment),
    }).then(handle);
  },

  async downloadCalendar() {
    // Can't use a plain <a href> for this like an unauthenticated static
    // file — the endpoint requires the Authorization header, which a
    // direct browser navigation can't attach. Fetch with auth, then
    // trigger the download client-side via a Blob URL instead.
    const res = await fetch(`${BASE}/courses/calendar.ics`, { headers: authHeaders() });
    if (res.status === 401) clearToken();
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "syllabussync.ics";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },
};
