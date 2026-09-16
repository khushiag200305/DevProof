import { useState } from "react";

interface ExtractionResult {
  filename: string;
  status: string;
  extracted_skills?: string[];
  github_links?: string[];
  text_preview?: string;
  error?: string;
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:8000/resumes/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setResult({ filename: file.name, status: "error", error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center px-4 py-16">
      <h1 className="text-3xl font-semibold text-slate-800">DevProof</h1>
      <p className="mt-2 text-slate-500 text-center max-w-md">
        Upload a resume PDF to extract claimed skills and GitHub links.
      </p>

      <div className="mt-8 bg-white rounded-lg shadow p-6 w-full max-w-md">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-600"
        />
        <button
          onClick={handleSubmit}
          disabled={!file || loading}
          className="mt-4 w-full bg-slate-800 text-white rounded-md py-2 disabled:opacity-40"
        >
          {loading ? "Analyzing..." : "Upload & Analyze"}
        </button>
      </div>

      {result && (
        <div className="mt-6 bg-white rounded-lg shadow p-6 w-full max-w-md text-sm">
          <p className="font-medium text-slate-700">{result.filename}</p>
          <p className="text-slate-500 mb-3">Status: {result.status}</p>

          {result.error && <p className="text-red-600">{result.error}</p>}

          {result.extracted_skills && (
            <div className="mb-3">
              <p className="font-medium text-slate-700">Detected skills:</p>
              <div className="flex flex-wrap gap-2 mt-1">
                {result.extracted_skills.length > 0 ? (
                  result.extracted_skills.map((skill) => (
                    <span
                      key={skill}
                      className="bg-slate-100 text-slate-700 rounded px-2 py-1 text-xs"
                    >
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-400 text-xs">None detected</span>
                )}
              </div>
            </div>
          )}

          {result.github_links && result.github_links.length > 0 && (
            <div>
              <p className="font-medium text-slate-700">GitHub links:</p>
              {result.github_links.map((link) => (
                <a
                  key={link}
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-blue-600 underline text-xs"
                >
                  {link}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;