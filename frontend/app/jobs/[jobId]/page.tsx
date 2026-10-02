"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  createJobEventSource,
  getJobEvents,
  getJobStatus,
  JobEvent,
  JobStatusResponse
} from "@/lib/api";

function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function estimateEta(startedAt?: string | null, processed?: number, total?: number): string {
  if (!startedAt || !processed || !total || processed <= 0) return "-";
  const elapsed = Date.now() - new Date(startedAt).getTime();
  const perChunk = elapsed / processed;
  const remaining = Math.max(total - processed, 0);
  const remainingMs = remaining * perChunk;
  const seconds = Math.max(Math.round(remainingMs / 1000), 0);
  const mm = Math.floor(seconds / 60);
  const ss = seconds % 60;
  return `${mm}m ${ss}s`;
}

function isActive(status?: string): boolean {
  return status === "queued" || status === "pending" || status === "processing";
}

export default function JobDetailPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let source: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;

    const bootstrap = async () => {
      try {
        const [statusData, eventData] = await Promise.all([getJobStatus(jobId), getJobEvents(jobId)]);
        setStatus(statusData);
        setEvents(eventData);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load initial job data");
      } finally {
        setLoading(false);
      }
    };

    const connect = () => {
      if (stopped) return;
      source = createJobEventSource(jobId);

      source.addEventListener("status_update", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent).data) as JobStatusResponse;
          setStatus((prev) => ({ ...(prev ?? {}), ...payload } as JobStatusResponse));
        } catch {
          // ignore malformed payload
        }
      });

      source.addEventListener("job_event", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent).data) as JobEvent;
          setEvents((prev) => {
            if (prev.some((e) => e.event_id === payload.event_id)) return prev;
            return [...prev, payload].sort((a, b) => a.event_id - b.event_id);
          });
        } catch {
          // ignore malformed payload
        }
      });

      source.addEventListener("done", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent).data) as { status?: string };
          const nextStatus = payload.status;
          if (nextStatus) {
            setStatus((prev) => {
              if (!prev) return prev;
              return { ...prev, status: nextStatus };
            });
          }
        } finally {
          source?.close();
        }
      });

      source.onerror = () => {
        source?.close();
        if (!stopped) {
          reconnectTimer = setTimeout(() => connect(), 2000);
        }
      };
    };

    bootstrap().then(connect);

    return () => {
      stopped = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      source?.close();
    };
  }, [jobId]);

  return (
    <main className="mx-auto max-w-5xl px-5 py-10">
      <Link href="/" className="mb-5 inline-block text-sm text-slate-600 hover:text-slate-900">
        ← Back to dashboard
      </Link>

      <header className="panel mb-6 p-6">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Job Detail</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">{jobId}</h1>

        {loading && (
          <div className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
            Loading live status...
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {error}
          </div>
        )}

        {status && (
          <div className="mt-4 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
            <p>
              Status: <span className="font-medium text-slate-900">{String(status.status ?? "-")}</span>
              {isActive(status.status) && (
                <span className="ml-2 inline-block h-3 w-3 animate-pulse rounded-full bg-sky-500" />
              )}
            </p>
            <p>Progress: <span className="font-medium text-slate-900">{String(status.progress ?? 0)}%</span></p>
            <p>Current Step: <span className="font-medium text-slate-900">{String(status.current_step ?? "-")}</span></p>
            <p>Updated: <span className="font-medium text-slate-900">{formatDate(String(status.completed_at ?? status.started_at ?? ""))}</span></p>
            <p>TTS Chunks: <span className="font-medium text-slate-900">{String(status.processed_tts_chunks ?? 0)}/{String(status.total_tts_chunks ?? 0)}</span></p>
            <p>Text Progress: <span className="font-medium text-slate-900">{String(status.processed_text_length ?? 0)}/{String(status.total_text_length ?? 0)} chars</span></p>
            <p>ETA: <span className="font-medium text-slate-900">{estimateEta(status.started_at, status.processed_tts_chunks, status.total_tts_chunks)}</span></p>
          </div>
        )}
      </header>

      <section className="panel overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-semibold">Timeline Events</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {events.length === 0 && <p className="px-5 py-4 text-sm text-slate-500">No events found.</p>}
          {events.map((event) => (
            <div key={event.event_id} className="px-5 py-4">
              <div className="flex items-center justify-between">
                <p className="font-medium">{event.event_type}</p>
                <p className="text-xs text-slate-500">{formatDate(event.timestamp)}</p>
              </div>
              <div className="mt-1 text-sm text-slate-600">
                <p>status: {event.status ?? "-"}</p>
                <p>progress: {event.progress ?? "-"}</p>
                <p>step: {event.step ?? "-"}</p>
              </div>
              {event.details && (
                <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                  {JSON.stringify(event.details, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
