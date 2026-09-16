import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StudentUpload } from "./StudentUpload";
import * as AuthContextModule from "../context/AuthContext";
import * as api from "../lib/api";

function pdfFile(name = "resume.pdf") {
  return new File(["%PDF-1.4 fake content"], name, { type: "application/pdf" });
}

describe("StudentUpload page", () => {
  beforeEach(() => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: { user_id: 1, email: "s@thapar.edu", name: "S", picture_url: null, role: "student" },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    vi.spyOn(api, "apiGet").mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderPage() {
    return render(
      <MemoryRouter>
        <StudentUpload />
      </MemoryRouter>
    );
  }

  it("renders the upload form with a manual GitHub URL override field", async () => {
    renderPage();
    expect(screen.getByLabelText(/resume pdf/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/github url \(optional override\)/i)).toBeInTheDocument();
    await waitFor(() => expect(api.apiGet).toHaveBeenCalledWith("/api/candidates/me"));
  });

  it("disables the upload button until a file is selected", async () => {
    renderPage();
    expect(screen.getByRole("button", { name: /upload & analyze/i })).toBeDisabled();
    await waitFor(() => expect(api.apiGet).toHaveBeenCalled());
  });

  it("uploads the resume and shows extracted skills plus a link to the full report", async () => {
    vi.spyOn(api, "apiUpload").mockResolvedValue({
      candidate_id: 7,
      filename: "resume.pdf",
      status: "parsed",
      name: "Aditi Sharma",
      extracted_skills: ["Python", "React"],
      projects: [],
      github_url: "github.com/aditisharma-dev",
      github_username: "aditisharma-dev",
    });

    const user = userEvent.setup();
    renderPage();

    await user.upload(screen.getByLabelText(/resume pdf/i), pdfFile());
    await user.click(screen.getByRole("button", { name: /upload & analyze/i }));

    await waitFor(() => expect(screen.getByText("Aditi Sharma")).toBeInTheDocument());
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view full report/i })).toHaveAttribute(
      "href",
      "/candidate/7"
    );

    expect(api.apiUpload).toHaveBeenCalledWith("/api/resume/upload", expect.any(FormData));
  });

  it("shows the API error message when the upload fails", async () => {
    vi.spyOn(api, "apiUpload").mockRejectedValue(new api.ApiError(403, "Not a student account."));

    const user = userEvent.setup();
    renderPage();
    await user.upload(screen.getByLabelText(/resume pdf/i), pdfFile());
    await user.click(screen.getByRole("button", { name: /upload & analyze/i }));

    await waitFor(() =>
      expect(screen.getByText("Not a student account.")).toBeInTheDocument()
    );
  });
});
