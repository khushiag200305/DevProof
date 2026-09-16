import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

function pdfFile(name = "resume.pdf") {
  return new File(["%PDF-1.4 fake content"], name, { type: "application/pdf" });
}

describe("App upload page", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: async () => ({
          candidate_id: 1,
          filename: "resume.pdf",
          status: "parsed",
          name: "Aditi Sharma",
          extracted_skills: ["Python", "React"],
          projects: ["DevProof Dashboard"],
          github_url: "github.com/aditisharma-dev",
          github_username: "aditisharma-dev",
        }),
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the upload form with a manual GitHub URL override field", () => {
    render(<App />);
    expect(screen.getByText("DevProof")).toBeInTheDocument();
    expect(screen.getByLabelText(/resume pdf/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/github url \(optional override\)/i)).toBeInTheDocument();
  });

  it("disables the upload button until a file is selected", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /upload & analyze/i })).toBeDisabled();
  });

  it("submits the resume and displays extracted skills and projects", async () => {
    const user = userEvent.setup();
    render(<App />);

    const fileInput = screen.getByLabelText(/resume pdf/i) as HTMLInputElement;
    await user.upload(fileInput, pdfFile());

    const button = screen.getByRole("button", { name: /upload & analyze/i });
    expect(button).toBeEnabled();
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByText("Aditi Sharma")).toBeInTheDocument();
    });
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("DevProof Dashboard")).toBeInTheDocument();

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/resume/upload"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("includes a manual GitHub URL override in the upload request when provided", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.upload(screen.getByLabelText(/resume pdf/i), pdfFile());
    await user.type(
      screen.getByLabelText(/github url \(optional override\)/i),
      "github.com/manual-override"
    );
    await user.click(screen.getByRole("button", { name: /upload & analyze/i }));

    await waitFor(() => expect(fetch).toHaveBeenCalled());
    const body = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
    expect(body.get("github_url_override")).toBe("github.com/manual-override");
  });
});
