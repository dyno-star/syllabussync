import { useState } from "react";
import { api } from "../api";

export default function LoginView({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await api.register(email, password);
      } else {
        await api.login(email, password);
      }
      onAuthenticated();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: 60 }}>
      <div className="card" style={{ padding: 36, maxWidth: 400, width: "100%" }}>
        <p
          style={{
            fontFamily: "var(--font-display)",
            fontStyle: "italic",
            fontWeight: 600,
            fontSize: 24,
            margin: "0 0 4px",
          }}
        >
          SyllabusSync
        </p>
        <p style={{ color: "var(--card-text-muted)", fontSize: 14, marginBottom: 24 }}>
          {mode === "login" ? "Sign in to see your courses." : "Create an account to get started."}
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ display: "grid", gap: 12, marginBottom: 18 }}>
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>

          {error && (
            <p
              style={{
                color: "var(--stamp-red)",
                fontSize: 13,
                marginBottom: 14,
                padding: "8px 12px",
                background: "var(--stamp-red-soft)",
                borderRadius: "var(--radius)",
              }}
            >
              {error}
            </p>
          )}

          <button type="submit" className="btn" style={{ width: "100%" }} disabled={loading}>
            {loading ? "…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 13, color: "var(--card-text-muted)", marginTop: 18 }}>
          {mode === "login" ? (
            <>
              Don't have an account?{" "}
              <button
                onClick={() => {
                  setMode("register");
                  setError(null);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--brass)",
                  cursor: "pointer",
                  fontSize: 13,
                  padding: 0,
                  textDecoration: "underline",
                }}
              >
                Create one
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                onClick={() => {
                  setMode("login");
                  setError(null);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--brass)",
                  cursor: "pointer",
                  fontSize: 13,
                  padding: 0,
                  textDecoration: "underline",
                }}
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
