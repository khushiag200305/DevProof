import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminRecruiters } from "./AdminRecruiters";
import { ProtectedRoute } from "../components/ProtectedRoute";
import * as AuthContextModule from "../context/AuthContext";
import * as api from "../lib/api";
import type { AuthUser } from "../context/AuthContext";

function signedInAs(user: AuthUser) {
  vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
    user,
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn().mockResolvedValue(undefined),
  });
}

const admin: AuthUser = {
  user_id: 1, email: "khushi@gmail.com", name: "Khushi", picture_url: null,
  role: "recruiter", recruiter_status: "approved", is_admin: true,
};

describe("Recruiter approval", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a waiting page to recruiters who aren't approved yet", () => {
    signedInAs({ ...admin, email: "hr@acme.com", name: "HR", is_admin: false, recruiter_status: "pending" });
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route path="/dashboard" element={<ProtectedRoute role="recruiter"><p>Candidates</p></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByRole("heading", { name: "Waiting for approval" })).toBeInTheDocument();
    expect(screen.queryByText("Candidates")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check again" })).toBeInTheDocument();
  });

  it("lets an admin approve a waiting recruiter", async () => {
    signedInAs(admin);
    vi.spyOn(api, "apiGet").mockResolvedValue([
      { user_id: 7, email: "hr@acme.com", name: "Neha Gupta", picture_url: null, domain: "acme.com", created_at: "2026-11-14T10:00:00Z", status: "pending" },
    ]);
    const put = vi.spyOn(api, "apiPut").mockResolvedValue({
      user_id: 7, email: "hr@acme.com", name: "Neha Gupta", picture_url: null, domain: "acme.com", created_at: "2026-11-14T10:00:00Z", status: "approved",
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AdminRecruiters />
      </MemoryRouter>
    );

    const row = await screen.findByRole("listitem", { name: "Neha Gupta" });
    expect(within(row).getByText("Waiting")).toBeInTheDocument();
    await user.click(within(row).getByRole("button", { name: "Approve" }));

    expect(put).toHaveBeenCalledWith("/api/admin/recruiters/7", { status: "approved" });
    expect(await within(row).findByText("Approved")).toBeInTheDocument();
    expect(within(row).getByRole("button", { name: "Revoke" })).toBeInTheDocument();
  });
});
