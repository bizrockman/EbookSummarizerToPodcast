"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { createEdition, createEditionAudio, Edition, getEdition, getJobStatus, getJobResult,
  getAudioBlob, JobStatusResponse, readingLevels, retryEdition } from "@/lib/api";

export default function EditionPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const [edition, setEdition] = useState<Edition | null>(null);
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [voice, setVoice] = useState("alloy");
  const [audioJob, setAudioJob] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState("");
  const [audioStatus, setAudioStatus] = useState("");
  const [reload, setReload] = useState(0);
  const lastReadSource = useRef("");

  useEffect(() => {
    if (!edition) return;
    function rememberSource() {
      const sections = Array.from(document.querySelectorAll<HTMLElement>("[data-source-id]"));
      const current = sections.filter(section => section.getBoundingClientRect().top <= 180).at(-1);
      if (current) lastReadSource.current = `#${current.id}`;
    }
    window.addEventListener("scroll", rememberSource, { passive: true });
    return () => window.removeEventListener("scroll", rememberSource);
  }, [edition]);

  useEffect(() => {
    if (!edition || !/^#s\d+$/.test(window.location.hash)) return;
    const frame = requestAnimationFrame(() => document.getElementById(window.location.hash.slice(1))?.scrollIntoView());
    return () => cancelAnimationFrame(frame);
  }, [edition]);

  function currentSourceAnchor() {
    const sections = Array.from(document.querySelectorAll<HTMLElement>("[data-source-id]"));
    const current = sections.filter(section => section.getBoundingClientRect().top <= 180).at(-1);
    return current ? `#${current.id}` : lastReadSource.current || window.location.hash;
  }

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await getJobStatus(jobId);
        if (!active) return;
        setStatus(next);
        if (next.status === "completed") {
          const result = await getEdition(jobId);
          if (active) setEdition(result);
        } else if (["failed", "cancelled"].includes(next.status)) {
          setError(next.error_message || "Die Erstellung wurde abgebrochen.");
        } else timer = setTimeout(poll, 2500);
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "Laden fehlgeschlagen"); }
    }
    setError("");
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId, reload]);

  useEffect(() => {
    if (!audioJob) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    let url = "";
    async function poll() {
      try {
        const next = await getJobStatus(audioJob!);
        if (!active) return;
        setAudioStatus(`${next.progress} % · ${next.current_step || next.status}`);
        if (next.status === "completed") {
          const result = await getJobResult(audioJob!);
          const asset = result.assets?.find(a => a.asset_type === "audio_combined");
          if (!asset) throw new Error("Keine Audiodatei gefunden");
          const blob = await getAudioBlob(audioJob!, asset.asset_id);
          if (active) { url = URL.createObjectURL(blob); setAudioUrl(url); }
        } else if (["failed", "cancelled"].includes(next.status)) {
          throw new Error(next.error_message || "Audioerstellung abgebrochen");
        } else timer = setTimeout(poll, 2500);
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "Audio fehlgeschlagen"); }
    }
    poll();
    return () => { active = false; clearTimeout(timer); if (url) URL.revokeObjectURL(url); };
  }, [audioJob, reload]);

  function downloadText() {
    if (!edition) return;
    const text = edition.sections.map(s => `${s.title}\n\n${s.text}`).join("\n\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url; link.download = `Lesefassung-${edition.level}.txt`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <main className="mx-auto max-w-5xl px-5 py-10">
    <Link href="/" className="text-sm text-slate-600">← Bibliothek</Link>
    <header className="my-8">
      <p className="text-xs uppercase tracking-[.2em] text-slate-500">Lesen und hören</p>
      <h1 className="mt-2 text-3xl font-semibold">{edition?.book_title || "Deine Lesefassung entsteht"}</h1>
      {edition ? <p className="mt-3 text-slate-600">{edition.label} · {edition.word_count.toLocaleString("de-DE")} Wörter · {Math.round(edition.actual_ratio * 100)} % des Originals · ca. {edition.estimated_minutes} Minuten Hörzeit</p>
        : <div className="mt-5" aria-live="polite"><p>{status?.current_step || "Lade Status …"}</p><progress className="mt-3 w-full" max={100} value={status?.progress || 0} /><p className="text-sm text-slate-500">Du kannst diese Seite schließen und später über die Bibliothek zurückkehren.</p></div>}
    </header>
    {error && <div role="alert" className="mb-6 rounded-xl bg-rose-50 p-4 text-rose-800">{error}<button className="ml-3 underline" onClick={() => setReload(n => n + 1)}>Erneut laden</button></div>}
    {status && (["failed", "cancelled"].includes(status.status) || edition?.quality_status === "length_warning") && <button disabled={busy} className="mb-6 rounded-lg border px-4 py-2" onClick={async () => {
      setBusy(true); try { const result = await retryEdition(jobId); window.location.assign(`/editions/${result.job_id}`); }
      catch (e) { setError(e instanceof Error ? e.message : "Neustart fehlgeschlagen"); setBusy(false); }
    }}>Mit gespeichertem Plan neu schreiben</button>}
    {edition && <>
      <section className="panel mb-8 p-5">
        <h2 className="font-semibold">Mehr oder weniger Tiefe</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-4">{readingLevels.map(level => <button key={level.id}
          disabled={busy || edition.level === level.id} aria-pressed={edition.level === level.id}
          className={`rounded-xl border p-3 text-left disabled:opacity-60 ${edition.level === level.id ? "border-emerald-700 bg-emerald-50" : "hover:bg-slate-50"}`}
          onClick={async () => { setBusy(true); setError(""); try {
            const anchor = currentSourceAnchor();
            const result = await createEdition(edition.book_id, edition.selected_chapters, level.id, edition.language);
            window.location.assign(`/editions/${result.job_id}${anchor}`);
          } catch (e) { setError(e instanceof Error ? e.message : "Fehler"); setBusy(false); } }}>
          <span className="block font-medium">{level.name}</span><span className="text-xs text-slate-500">{level.description}</span>
        </button>)}</div>
        <p className="mt-3 text-sm text-slate-500">Jede Fassung greift auf das Original zurück. Bereits erstellte Stufen werden wieder geöffnet.</p>
      </section>
      {edition.warnings.length > 0 && <aside className="mb-6 rounded-xl bg-amber-50 p-4"><h2 className="font-semibold">Diese Fassung weicht vom Längenziel ab</h2><p>Die tatsächliche Länge steht oben. Du kannst diese Fassung verwenden oder einen neuen Schreibversuch starten.</p><ul className="mt-2 list-disc pl-5">{edition.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></aside>}
      <section className="panel mb-8 flex flex-wrap items-center gap-3 p-5">
        <button className="rounded-lg border px-4 py-2" onClick={downloadText}>Text herunterladen</button>
        <label className="text-sm">Stimme <select className="ml-2 rounded-lg border p-2" value={voice} onChange={e => setVoice(e.target.value)}>{["alloy", "echo", "fable", "onyx", "nova", "shimmer"].map(v => <option key={v}>{v}</option>)}</select></label>
        <button disabled={busy || !!audioJob || !["automated_review_passed", "length_warning"].includes(edition.quality_status)} className="rounded-lg bg-ink px-4 py-2 text-white disabled:opacity-50" onClick={async () => {
          setBusy(true); setError(""); try { const result = await createEditionAudio(jobId, voice); setAudioJob(result.job_id); }
          catch (e) { setError(e instanceof Error ? e.message : "Audio fehlgeschlagen"); } finally { setBusy(false); }
        }}>Diese Fassung vertonen</button>
        {audioJob && <Link className="text-sm underline" href={`/jobs/${audioJob}`}>{audioStatus || "Audio wird vorbereitet …"}</Link>}
        {audioUrl && <div className="w-full"><audio controls src={audioUrl} className="mt-3 w-full" /><a href={audioUrl} download="hoerbuch.mp3" className="mt-2 inline-block text-sm underline">MP3 herunterladen</a></div>}
      </section>
      <p className="mb-6 text-sm text-slate-500">Automatisch mit den Quellen abgeglichen. Das ersetzt keine redaktionelle Prüfung; du kannst jeden Abschnitt mit dem Original vergleichen.</p>
      {!!edition.empty_chapters?.length && <p className="mb-6 text-sm text-slate-500">Ohne auslesbaren Text: {edition.empty_chapters.join(", ")}.</p>}
      <p className="mb-6 text-xs text-slate-500">{edition.billing_note}</p>
      <nav aria-label="Kapitel der Lesefassung" className="panel mb-8 p-5"><h2 className="mb-3 font-semibold">Kapitel</h2><ol className="space-y-2">{edition.sections.filter((section, i) => i === 0 || edition.sections[i - 1].href !== section.href).map(section => <li key={section.source_id}><a className="text-sm underline" href={`#${section.source_id}`}>{section.title}</a></li>)}</ol></nav>
      <article className="mx-auto max-w-2xl">{edition.sections.map((section, i) => <section key={section.source_id} id={section.source_id} data-source-id={section.source_id} className="mb-8 scroll-mt-6">
        {(i === 0 || edition.sections[i - 1].href !== section.href) && <h2 className="mb-5 text-2xl font-semibold">{section.title}</h2>}
        <div className="whitespace-pre-line font-serif text-lg leading-relaxed">{section.text}</div>
        <details className="mt-4 rounded-lg border border-slate-200 p-3 text-sm"><summary className="cursor-pointer text-slate-500">Originalstelle vergleichen · {section.source_id}</summary><p className="mt-3 whitespace-pre-line leading-relaxed">{section.source_text}</p></details>
      </section>)}</article>
    </>}
  </main>;
}
