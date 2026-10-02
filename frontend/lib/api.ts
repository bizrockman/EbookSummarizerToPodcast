export type Job = {
  job_id: string;
  job_type: string;
  status: string;
  book_title?: string;
  progress: number;
  created_at: string;
  completed_at?: string;
  total_cost_usd: number;
  input_tokens?: number;
  output_tokens?: number;
  strategy?: string;
  language?: string;
  audio?: boolean;
  cost_is_complete?: boolean;
};

export type Book = {
  book_id: string;
  title?: string;
  author?: string;
  filename: string;
  chapter_count: number;
  is_analyzed: boolean;
  total_cost_usd: number;
  uploaded_at: string;
};

export type Chapter = {
  title: string;
  href: string;
  chapter_type?: "content" | "supplement" | null;
  order?: number | null;
};

export type ChapterAnalysisResponse = {
  book_title?: string;
  book_author?: string;
  all_chapters: Chapter[];
  content_chapters: Chapter[];
  supplement_chapters: Chapter[];
  total_chapters: number;
  content_count: number;
  supplement_count: number;
  analysis_cost_usd: number;
  from_cache: boolean;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
};

export type JobEvent = {
  event_id: number;
  timestamp: string;
  event_type: string;
  status?: string | null;
  progress?: number | null;
  step?: string | null;
  details?: Record<string, unknown> | null;
};

export type JobStatusResponse = {
  job_id: string;
  job_type: string;
  status: string;
  progress: number;
  current_step?: string | null;
  completed_at?: string | null;
  started_at?: string | null;
  error_message?: string | null;
  total_text_length?: number;
  processed_text_length?: number;
  total_tts_chunks?: number;
  processed_tts_chunks?: number;
  costs?: {
    total_cost_usd: number;
    llm_cost_usd: number;
    tts_cost_usd: number;
  };
};

export type JobResultResponse = {
  status: string;
  combined_audio_file?: string | null;
  total_duration_seconds?: number;
  assets?: { asset_id: string; asset_type: string; file_name: string }[];
};

export type ReadingLevel = "light" | "standard" | "compact" | "essence";
export type Edition = {
  job_id: string; book_id: string; book_title: string; level: ReadingLevel; label: string;
  language: string; source_words: number; word_count: number; actual_ratio: number;
  estimated_minutes: number; quality_status: string; warnings: string[];
  selected_chapters: string[]; empty_chapters?: string[]; billing_note?: string;
  sections: { source_id: string; href: string; title: string; text: string; source_text: string }[];
};

export const readingLevels: { id: ReadingLevel; name: string; description: string }[] = [
  { id: "light", name: "Behutsam", description: "ca. 65 % · Viel Tiefe, weniger Wiederholung" },
  { id: "standard", name: "Verdichtet", description: "ca. 35 % · Argumente und starke Beispiele" },
  { id: "compact", name: "Kompakt", description: "ca. 12 % · Die zentralen Gedanken" },
  { id: "essence", name: "Essenz", description: "ca. 4 % · Ein kurzer Einstieg ins Werk" },
];

export function createEdition(bookId: string, chapters: string[], level: ReadingLevel, language: string) {
  return apiFetch<{ job_id: string }>("/summaries", "POST", { book_id: bookId, chapters, level, language });
}

export function getEdition(jobId: string) {
  return apiFetch<Edition>(`/summaries/${jobId}`);
}

export function retryEdition(jobId: string) {
  return apiFetch<{ job_id: string }>(`/summaries/${jobId}/retry`, "POST", {});
}

export function createEditionAudio(jobId: string, voice: string) {
  return apiFetch<{ job_id: string }>(`/summaries/${jobId}/audio`, "POST", { voice });
}

export async function getAudioBlob(jobId: string, assetId: string): Promise<Blob> {
  const response = await fetch(`${BASE_URL}/jobs/${jobId}/assets/${assetId}/download`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!response.ok) throw new Error("Audiodatei konnte nicht geladen werden");
  return response.blob();
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "dummy-api-key-12345";

type Body = Record<string, unknown> | FormData | undefined;

export async function apiFetch<T>(path: string, method: "GET" | "POST" | "DELETE" = "GET", body?: Body): Promise<T> {
  const headers: Record<string, string> = {
    "X-API-Key": API_KEY
  };

  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: payload,
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    let detail: unknown;
    try { detail = JSON.parse(text).detail; } catch { /* The API can also return plain text. */ }
    if (typeof detail === "string") throw new Error(detail);
    throw new Error(`API ${response.status} for ${path}: ${text}`);
  }
  return response.json() as Promise<T>;
}

export async function getBooks(): Promise<Book[]> {
  const result = await apiFetch<{ books: Book[] }>("/books");
  return result.books;
}

export function getBookDetails(bookId: string) {
  return apiFetch<Book & { chapters_raw: Chapter[] }>(`/books/${bookId}`);
}

export async function getJobs(): Promise<Job[]> {
  const result = await apiFetch<{ jobs: Job[] }>("/jobs?page=1&page_size=20");
  return result.jobs;
}

export function getJobPage(page: number) {
  return apiFetch<{ jobs: Job[]; total_count: number }>(`/jobs?page=${page}&page_size=20`);
}

export function cancelJob(jobId: string) {
  return apiFetch(`/jobs/${jobId}`, "DELETE");
}

export async function uploadEpub(file: File): Promise<Book> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<Book>("/books/upload", "POST", formData);
}

export async function analyzeBookChapters(bookId: string): Promise<ChapterAnalysisResponse> {
  return apiFetch<ChapterAnalysisResponse>("/epub/analyze-chapters", "POST", {
    book_id: bookId
  });
}

export async function createAudiobookFromChapters(
  bookId: string,
  chapters: string[],
  voice = "alloy"
): Promise<{ job_id: string }> {
  return apiFetch<{ job_id: string }>("/audiobook/chapters", "POST", {
    book_id: bookId,
    chapters,
    tts_provider: "openai",
    voice
  });
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return apiFetch<JobStatusResponse>(`/jobs/${jobId}`);
}

export async function getJobResult(jobId: string): Promise<JobResultResponse> {
  return apiFetch<JobResultResponse>(`/jobs/${jobId}/result`);
}

export async function getJobEvents(jobId: string): Promise<JobEvent[]> {
  const result = await apiFetch<{ events: JobEvent[] }>(`/jobs/${jobId}/events`);
  return result.events;
}

export function createJobEventSource(jobId: string): EventSource {
  const url = `${BASE_URL}/jobs/${jobId}/stream?api_key=${encodeURIComponent(API_KEY)}`;
  return new EventSource(url);
}
