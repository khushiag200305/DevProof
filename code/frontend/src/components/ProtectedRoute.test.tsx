import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "./ProtectedRoute";
import * as AuthContextModule from "../context/AuthContext";

function renderAt(path: string, role?: "student" | "recruiter") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<p>login page</p>} />
        <Route path="/upload" element={<p>student home</p>} />
        <Route path="/dashboard" element={<p>recruiter home</p>} />
        <Route
          path="/protected"
          element={
            <ProtectedRoute role={role}>
              <p>protected content</p>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("shows a loading state while auth is resolving", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: null,
      loading: true,
      login: vi.fn(),
      logout: vi.fn(),
    });
    renderAt("/protected");
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("redirects unauthenticated users to /login", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: null,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    renderAt("/protected");
    expect(screen.getByText("login page")).toBeInTheDocument();
  });

  it("redirects a recruiter away from a student-only route to their own home", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: {
        user_id: 1,
        email: "r@acme.com",
        name: "R",
        picture_url: null,
        role: "recruiter",
      },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    renderAt("/protected", "student");
    expect(screen.getByText("recruiter home")).toBeInTheDocument();
  });

  it("renders the protected content for a matching role", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: {
        user_id: 1,
        email: "s@thapar.edu",
        name: "S",
        picture_url: null,
        role: "student",
      },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    renderAt("/protected", "student");
    expect(screen.getByText("protected content")).toBeInTheDocument();
  });

  it("renders content for any authenticated role when no role is required", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: {
        user_id: 1,
        email: "r@acme.com",
        name: "R",
        picture_url: null,
        role: "recruiter",
      },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    renderAt("/protected");
    expect(screen.getByText("protected content")).toBeInTheDocument();
  });
});
