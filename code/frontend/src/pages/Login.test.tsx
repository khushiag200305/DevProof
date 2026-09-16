import { GoogleOAuthProvider } from "@react-oauth/google";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Login } from "./Login";
import * as AuthContextModule from "../context/AuthContext";

function renderLogin() {
  return render(
    <GoogleOAuthProvider clientId="test-client-id">
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    </GoogleOAuthProvider>
  );
}

describe("Login page", () => {
  it("shows the DevProof branding and role-derivation hint", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: null,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    renderLogin();

    expect(screen.getByRole("heading", { name: "DevProof" })).toBeInTheDocument();
    expect(screen.getByText(/@thapar\.edu/)).toBeInTheDocument();
    expect(screen.getByText(/gives you a student account/i)).toBeInTheDocument();
  });

  it("redirects an already signed-in student to /upload", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: { user_id: 1, email: "s@thapar.edu", name: "S", picture_url: null, role: "student" },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    render(
      <GoogleOAuthProvider clientId="test-client-id">
        <MemoryRouter initialEntries={["/login"]}>
          <Login />
        </MemoryRouter>
      </GoogleOAuthProvider>
    );

    expect(screen.queryByRole("heading", { name: "DevProof" })).not.toBeInTheDocument();
  });
});
