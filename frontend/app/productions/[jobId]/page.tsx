"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { cancelJob, getAudioBlob } from "@/lib/api";
import { getProduction, getStudioOptions, Production, retryProduction, numbers, statuses } from "@/lib/studio";
import UsagePanel from "@/components/UsagePanel";

function download(content: string, name: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a"); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

export default function ProductionPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const [job, setJob] = useState<Production | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const [audioUrl, setAudioUrl] = useState("");
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [retryModel, setRetryModel] = useState<string | null>(null);
  const [workersDisabled, setWorkersDisabled] = useState(false);
  useEffect(() => { setRetryModel(null); }, [jobId]);
  useEffect(() => {
    let active = true;
    getStudioOptions().then(options => { if (active) setWorkersDisabled(options.worker_threads === 0); }).catch(() => {});
    return () => { active = false; };
  }, [jobId, reload]);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await getProduction(jobId);
        if (!active) return;
        setJob(next); setError("");
        if (["queued", "pending", "processing"].includes(next.status)) timer = setTimeout(poll, 3000);
      } catch (e) {
        if (active) { setError(e instanceof Error ? e.message : String(e)); timer = setTimeout(poll, 8000); }
      }
    }
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId, reload]);
  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl); }, [audioUrl]);
  const result = job?.result;
  const running = !!job && ["queued", "pending", "processing"].includes(job.status);
  const failed = !!job && ["failed", "cancelled"].includes(job.status);
  return <main className="mx-auto max-w-5xl px-5 py-10">
    <Link href="/" className="text-sm text-slate-600">← Bibliothek und alle Aufträge</Link>
    <header className="my-8"><p className="text-xs uppercase tracking-[.2em] text-slate-500">{result?.label || "Dein Buchauftrag"}</p><h1 className="mt-2 text-3xl font-semibold">{job?.book_title || "Lade Auftrag..."}</h1>
      {result && <p className="mt-3 text-slate-600">{numbers(result.word_count)} Wörter · {Math.round(result.actual_ratio * 100)} % der ausgewählten Originalkapitel · ca. {result.estimated_minutes} Minuten Hörzeit{result.language !== "original" && ` · ${result.language.toUpperCase()}`}</p>}
      {job && <p className="mt-3 text-sm text-slate-600">{job.config.chapters.length} ausgewählte Kapitel · {job.config.strategy === "reading" ? `Lesefassung mit ${Math.round(job.config.ratio * 100)} % Ziellänge` : job.config.strategy === "core" ? `Kernfassung mit ${numbers(job.config.core_words)} Wörtern` : "Originalfassung"} · {job.config.language === "original" ? "Originalsprache" : job.config.language.toUpperCase()}{job.config.audio && " · mit Hörbuch"}</p>}
    </header>
    {error && <p role="alert" className="mb-6 rounded-xl bg-rose-50 p-4 text-rose-800">{error}<button className="ml-3 underline" onClick={() => setReload(n => n + 1)}>Erneut laden</button></p>}
    {job && <section className="panel mb-6 p-5" aria-live="polite"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold">{statuses[job.status] || job.status} · {job.progress} %</p><p className="mt-1 text-sm text-slate-600">{job.current_step || "Warte auf Worker"}</p></div>
      {running && <button disabled={busy} className="button-secondary" onClick={async () => { setBusy(true); try { await cancelJob(jobId); setReload(n => n + 1); } catch (e) { setError(String(e)); } finally { setBusy(false); } }}>Auftrag abbrechen</button>}
      {failed && <button disabled={busy} className="button-primary" onClick={async () => { setBusy(true); try { const next = await retryProduction(jobId, retryModel ?? job.config.text_model); window.location.assign(`/productions/${next.job_id}`); } catch (e) { setError(e instanceof Error ? e.message : String(e)); setBusy(false); } }}>Mit gespeicherten Schritten fortsetzen</button>}</div>
      <progress className="mt-3 w-full" max={100} value={job.progress} />
      {running && <p className="mt-3 text-sm text-slate-500">Du kannst weitere Aufträge starten und später zurückkehren. Beim Abbrechen wird ein bereits laufender API-Aufruf noch erfasst.</p>}
      {running && workersDisabled && <p role="status" className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">In dieser App-Konfiguration sind keine Worker gestartet. Der Auftrag wartet und wird erst nach dem Worker-Start verarbeitet.</p>}
      {job.error_message && <p className="mt-3 text-sm text-rose-800">{job.error_message}</p>}
      {failed && (job.config.strategy !== "original" || job.config.language !== "original") && <details className="mt-4 text-sm"><summary className="cursor-pointer text-slate-600">Modell für das Fortsetzen prüfen oder ändern</summary><label className="mt-3 block">Textmodell<input list="retry-models" disabled={busy} value={retryModel ?? job.config.text_model ?? ""} onChange={e => setRetryModel(e.target.value)} className="ml-3 max-w-full rounded-lg border p-2" /></label><datalist id="retry-models"><option value="gpt-5" /><option value="gpt-6.1-sol" /></datalist><p className="mt-2 text-xs text-slate-500">Der API-Modellname wird vor dem Fortsetzen geprüft. Bei einem Modellwechsel werden Textschritte neu berechnet; gespeicherte Ergebnisse bleiben erhalten.</p></details>}
      {failed && result && <p className="mt-3 text-sm text-slate-500">Die Textfassung bleibt verfügbar. Erfolgreiche Text- und Audioschritte werden beim Fortsetzen wiederverwendet.</p>}
      {job.config.retry_of && <p className="mt-3 text-sm text-slate-500">Die Anzeige zählt nur diesen Versuch. Verbrauch des vorherigen Versuchs: <Link className="underline" href={`/productions/${job.config.retry_of}`}>vorherigen Auftrag öffnen</Link>.</p>}
    </section>}
    {job && <UsagePanel usage={job.usage} />}
    {result && <>
      <section className="panel my-6 flex flex-wrap items-center gap-3 p-5"><button className="button-secondary" onClick={() => download(result.sections.map(s => `${s.title}\n\n${s.text}`).join("\n\n"), `${result.label}.txt`, "text/plain;charset=utf-8")}>Text herunterladen</button>
        <button className="button-secondary" onClick={() => download(JSON.stringify(job?.usage, null, 2), "verbrauch.json", "application/json")}>Verbrauch exportieren</button>
        <Link className="button-secondary" href={`/workflow?book=${job?.book_id}`}>Andere Fassung erstellen</Link>
        {result.audio.length > 0 && !audioUrl && <button disabled={loadingAudio} className="button-primary" onClick={async () => {
          setLoadingAudio(true); try { const blob = await getAudioBlob(jobId, result.audio[0].asset_id); setAudioUrl(URL.createObjectURL(blob)); } catch (e) { setError(String(e)); } finally { setLoadingAudio(false); }
        }}>{loadingAudio ? "Lade Hörbuch..." : "Hörbuch laden"}</button>}
        {audioUrl && <div className="w-full"><p className="mb-2 text-xs text-slate-500">Dieses Hörbuch verwendet eine KI-generierte Stimme.</p><audio controls src={audioUrl} className="w-full" /><a className="mt-3 inline-block text-sm underline" href={audioUrl} download="hoerbuch.mp3">MP3 herunterladen</a></div>}
      </section>
      {result.warnings.length > 0 && <aside className="mb-6 rounded-xl bg-amber-50 p-4"><h2 className="font-semibold">Hinweise zur Fassung</h2><ul className="mt-2 list-disc pl-5 text-sm">{result.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></aside>}
      {!!result.empty_chapters?.length && <p className="mb-6 text-sm text-slate-500">Ohne auslesbaren Text: {result.empty_chapters.join(", ")}</p>}
      <p className="mb-6 text-sm text-slate-500">{result.strategy === "original" && result.language === "original" ? "Aus der EPUB-Datei ausgelesener Originaltext. " : "Die Fassung wurde automatisch erstellt und noch nicht redaktionell geprüft. "}Du kannst die Originalstellen direkt vergleichen. Prozentangaben nach einer Übersetzung sind sprachabhängig.</p>
      <nav aria-label="Kapitel dieser Fassung" className="panel mb-8 p-5"><h2 className="mb-3 font-semibold">Inhalt</h2><ol className="space-y-2">{result.sections.filter((s, i) => i === 0 || result.sections[i - 1].href !== s.href).map(s => <li key={s.source_id}><a className="text-sm underline" href={`#${s.source_id}`}>{s.title}</a></li>)}</ol></nav>
      <article className="mx-auto max-w-2xl">{result.sections.map((s, i) => <section key={s.source_id} id={s.source_id} className="mb-9 scroll-mt-5">
        {(i === 0 || result.sections[i - 1].href !== s.href) && <h2 className="mb-5 text-2xl font-semibold">{s.title}</h2>}
        <div className="whitespace-pre-line font-serif text-lg leading-relaxed">{s.text}</div>
        <details className="mt-4 rounded-xl border p-3 text-sm"><summary className="cursor-pointer text-slate-500">Originalstelle vergleichen</summary><p className="mt-3 max-h-96 overflow-auto whitespace-pre-line leading-relaxed">{s.source_text}</p></details>
        {s.pre_translation_text && <details className="mt-3 rounded-xl border p-3 text-sm"><summary className="cursor-pointer text-slate-500">Fassung vor der Übersetzung</summary><p className="mt-3 whitespace-pre-line leading-relaxed">{s.pre_translation_text}</p></details>}
      </section>)}</article>
    </>}
  </main>;
}
