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

  it("deletes an upload from the history after confirming", async () => {
    const khushi = { candidate_id: 2, name: "Khushi Agarwal", github_username: "k", created_at: "2026-10-11T08:00:00Z", skill_count: 36, visible_to_recruiters: true };
    vi.spyOn(api, "apiGet")
      .mockResolvedValueOnce([
        { candidate_id: 4, name: "Rohit Singhal", github_username: null, created_at: "2026-10-15T08:00:00Z", skill_count: 18, visible_to_recruiters: false },
        khushi,
      ])
      .mockResolvedValue([khushi]);
    const del = vi.spyOn(api, "apiDelete").mockResolvedValue();
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Delete upload Rohit Singhal" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Delete Rohit Singhal?");
    expect(del).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete upload" }));

    expect(del).toHaveBeenCalledWith("/api/candidates/4");
    await waitFor(() => expect(screen.queryByText("Rohit Singhal")).not.toBeInTheDocument());
    expect(screen.getByText("Khushi Agarwal")).toBeInTheDocument();
  });

  it("makes another upload visible to recruiters", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue([
      { candidate_id: 5, name: "New resume", github_username: "k", created_at: "2026-11-01T08:00:00Z", skill_count: 20, visible_to_recruiters: false },
      { candidate_id: 2, name: "Old resume", github_username: "k", created_at: "2026-10-11T08:00:00Z", skill_count: 36, visible_to_recruiters: true },
    ]);
    const put = vi.spyOn(api, "apiPut").mockResolvedValue({ visible_candidate_id: 5 });
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /^Make New resume uploaded .* visible to recruiters$/ }));

    expect(put).toHaveBeenCalledWith("/api/candidates/5/visible", {});
    expect(await screen.findByRole("button", { name: /^Make Old resume uploaded/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Make New resume uploaded/ })).not.toBeInTheDocument();
    expect(screen.getAllByText("Visible to recruiters")).toHaveLength(1);
  });

  it("asks whether a new upload should replace the visible resume", async () => {
    vi.spyOn(api, "apiUpload").mockResolvedValue({
      candidate_id: 9, filename: "resume.pdf", status: "parsed", name: "Khushi Agarwal",
      extracted_skills: ["Python"], visible_to_recruiters: false,
    });
    const put = vi.spyOn(api, "apiPut").mockResolvedValue({ visible_candidate_id: 9 });
    const user = userEvent.setup();
    renderPage();

    await user.upload(screen.getByLabelText(/resume pdf/i), pdfFile());
    await user.click(screen.getByRole("button", { name: /upload & analyze/i }));

    expect(await screen.findByText(/make this resume visible to recruiters instead/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yes, make visible" }));
    expect(put).toHaveBeenCalledWith("/api/candidates/9/visible", {});
    expect(await screen.findByText("Visible to recruiters")).toBeInTheDocument();
  });
});
