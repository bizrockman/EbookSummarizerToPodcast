import { apiFetch } from "./api";

export type Strategy = "reading" | "core" | "original";
export type StudioChapter = {
  href: string; title: string; order: number; word_count: number; excerpt: string;
  selected: boolean; chapter_type: string; selection_reason: string;
};
export type StudioOptions = {
  strategies: { id: string; label: string }[]; text_providers: string[]; audio_providers: string[];
  text_model: string; audio_model: string; audio_available: boolean; voices: string[]; worker_threads: number;
  suggested_text_models: string[];
};
export type ProductionInput = {
  book_id: string; chapters: string[]; strategy: Strategy; ratio: number; core_words: number;
  language: string; audio: boolean; voice: string; text_provider: string; audio_provider: string; text_model?: string;
};
export type UsageTotals = {
  calls: number; input: number; output: number; cached_input: number; cache_write: number; reasoning: number;
  characters: number; known_cost_usd: number; unknown_calls: number; cache_hits: number;
};
export type UsageReport = {
  totals: UsageTotals; estimated_cost_usd: number | null; note: string;
  phases: (UsageTotals & { phase: string })[];
  calls: { id: number; phase: string; model: string; provider: string; status: string;
    input: number | null; output: number | null; cost_usd: number | null; seconds?: number; }[];
};
export type Production = {
  job_id: string; book_id: string; book_title: string; status: string; progress: number;
  current_step: string; error_message?: string; config: ProductionInput & { retry_of?: string };
  usage: UsageReport;
  result: null | { strategy: Strategy; label: string; language: string; source_words: number;
    word_count: number; actual_ratio: number; estimated_minutes: number; warnings: string[];
    empty_chapters?: string[];
    sections: { source_id: string; href: string; title: string; text: string; source_text: string;
      pre_translation_text?: string; target_words?: number }[];
    audio: { asset_id: string; duration_seconds: number }[];
  };
};

export const getStudioOptions = () => apiFetch<StudioOptions>("/productions/options");
export const getStudioChapters = (bookId: string) => apiFetch<{ chapters: StudioChapter[]; total_words: number }>(`/productions/books/${bookId}/chapters`);
export const createProduction = (input: ProductionInput) => apiFetch<{ job_id: string; reused: boolean }>("/productions", "POST", input);
export const getProduction = (jobId: string) => apiFetch<Production>(`/productions/${jobId}`);
export const retryProduction = (jobId: string, textModel?: string) => apiFetch<{ job_id: string }>(`/productions/${jobId}/retry`, "POST", textModel ? { text_model: textModel } : {});
export const numbers = (value: number) => value.toLocaleString("de-DE");
export const dollars = (value: number) => value.toLocaleString("de-DE", { style: "currency", currency: "USD", minimumFractionDigits: 4 });
export const statuses: Record<string, string> = { queued: "Wartet", pending: "Wartet", processing: "In Bearbeitung", completed: "Fertig", failed: "Fehlgeschlagen", cancelled: "Abgebrochen" };
