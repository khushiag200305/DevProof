import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthContext";
import * as api from "../lib/api";

const fakeUser = {
  user_id: 1,
  email: "student@thapar.edu",
  name: "Test Student",
  picture_url: null,
  role: "student" as const,
};

function Probe() {
  const { user, loading, login, logout } = useAuth();
  if (loading) return <p>loading</p>;
  return (
    <div>
      <p>{user ? `signed in as ${user.email} (${user.role})` : "signed out"}</p>
      <button onClick={() => login("fake-token", fakeUser)}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts signed out with no stored session", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByText("signed out")).toBeInTheDocument());
  });

  it("login() stores the session and updates the user", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByText("signed out")).toBeInTheDocument());

    act(() => screen.getByText("login").click());

    expect(screen.getByText("signed in as student@thapar.edu (student)")).toBeInTheDocument();
    expect(localStorage.getItem("devproof_token")).toBe("fake-token");
  });

  it("logout() clears the session", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByText("signed out")).toBeInTheDocument());

    act(() => screen.getByText("login").click());
    expect(screen.getByText(/signed in as/)).toBeInTheDocument();

    act(() => screen.getByText("logout").click());
    expect(screen.getByText("signed out")).toBeInTheDocument();
    expect(localStorage.getItem("devproof_token")).toBeNull();
  });

  it("restores a stored session and refreshes it from /api/auth/me", async () => {
    localStorage.setItem("devproof_token", "stored-token");
    localStorage.setItem("devproof_user", JSON.stringify(fakeUser));
    vi.spyOn(api, "apiGet").mockResolvedValue({ ...fakeUser, name: "Refreshed Name" });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await waitFor(() =>
      expect(screen.getByText("signed in as student@thapar.edu (student)")).toBeInTheDocument()
    );
  });

  it("clears a stored session if /api/auth/me rejects it", async () => {
    localStorage.setItem("devproof_token", "stale-token");
    localStorage.setItem("devproof_user", JSON.stringify(fakeUser));
    vi.spyOn(api, "apiGet").mockRejectedValue(new api.ApiError(401, "invalid"));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByText("signed out")).toBeInTheDocument());
    expect(localStorage.getItem("devproof_token")).toBeNull();
  });
});
