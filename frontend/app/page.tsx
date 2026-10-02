"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Book, Job, getBooks, getJobPage } from "@/lib/api";
import { numbers, dollars, statuses } from "@/lib/studio";

export default function DashboardPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const [list, result] = await Promise.all([getBooks(), getJobPage(page)]);
        if (active) { setBooks(list); setJobs(result.jobs); setTotal(result.total_count); setError(""); }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : String(e)); }
      finally { if (active) timer = setTimeout(poll, 4000); }
    }
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [page]);
  const activeJobs = jobs.filter(j => ["processing", "queued", "pending"].includes(j.status)).length;
  return <main className="mx-auto max-w-6xl px-5 py-10">
    <header className="mb-8 flex flex-wrap items-end justify-between gap-5"><div><p className="text-xs uppercase tracking-[.2em] text-slate-500">Deine Bibliothek</p><h1 className="mt-2 text-4xl font-semibold">Ebook Audio Studio</h1><p className="mt-3 text-slate-600">Bücher kürzen, übersetzen und unterwegs hören.</p></div><Link href="/workflow" className="button-primary">Neuen Auftrag erstellen</Link></header>
    {error && <p role="alert" className="mb-6 rounded-xl bg-rose-50 p-4 text-rose-800">Die API ist noch nicht erreichbar. {error}</p>}
    <section className="mb-8 grid gap-4 sm:grid-cols-3"><div className="panel p-5"><p className="text-sm text-slate-500">Bücher</p><p className="mt-1 text-3xl font-semibold">{books.length}</p></div><div className="panel p-5"><p className="text-sm text-slate-500">Aktive Aufträge auf dieser Seite</p><p className="mt-1 text-3xl font-semibold">{activeJobs}</p></div><div className="panel p-5"><p className="text-sm text-slate-500">Input / Output auf dieser Seite</p><p className="mt-1 text-2xl font-semibold">{numbers(jobs.reduce((n, j) => n + (j.input_tokens || 0), 0))} / {numbers(jobs.reduce((n, j) => n + (j.output_tokens || 0), 0))}</p><p className="mt-2 text-xs text-slate-500">Details und Kostenschätzung stehen im jeweiligen Auftrag.</p></div></section>
    <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]"><div className="panel overflow-hidden"><div className="flex items-center justify-between border-b px-5 py-4"><h2 className="text-lg font-semibold">Aufträge</h2><span className="text-xs text-slate-500">{total} insgesamt · aktualisiert automatisch</span></div>
      <div className="divide-y">{!jobs.length && <p className="p-5 text-sm text-slate-500">Noch keine Aufträge. Lade ein EPUB hoch und wähle deine erste Fassung.</p>}{jobs.map(job => <Link key={job.job_id} href={job.job_type === "book_processing" ? `/productions/${job.job_id}` : job.job_type === "book_summary" ? `/editions/${job.job_id}` : `/jobs/${job.job_id}`} className="block p-5 hover:bg-slate-50"><div className="flex items-center justify-between gap-3"><p className="font-medium">{job.book_title || "Buchauftrag"}</p><span className={`text-sm ${job.status === "failed" ? "text-rose-700" : job.status === "completed" ? "text-emerald-700" : "text-slate-500"}`}>{statuses[job.status] || job.status}</span></div><p className="mt-1 text-xs text-slate-500">{job.strategy === "reading" ? "Lesefassung" : job.strategy === "core" ? "Kernfassung" : job.strategy === "original" ? "Original" : job.job_type === "book_summary" ? "Lesefassung, früherer Ansatz" : "Hörbuch / Analyse"}{job.language && job.language !== "original" && ` · ${job.language.toUpperCase()}`}{job.audio && " · mit Audio"} · {job.progress} %</p><progress className="mt-3 h-1 w-full" max={100} value={job.progress} /><div className="mt-2 flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>Input {numbers(job.input_tokens || 0)} / Output {numbers(job.output_tokens || 0)}</span><span>{dollars(job.total_cost_usd)} geschätzt{job.cost_is_complete === false && " + offen"}</span></div></Link>)}</div>
      {total > 20 && <div className="flex items-center justify-between border-t p-4"><button className="button-secondary" disabled={page === 1} onClick={() => setPage(n => n - 1)}>Zurück</button><span className="text-sm">Seite {page} von {Math.ceil(total / 20)}</span><button className="button-secondary" disabled={page * 20 >= total} onClick={() => setPage(n => n + 1)}>Weiter</button></div>}</div>
      <div className="panel self-start overflow-hidden"><h2 className="border-b px-5 py-4 text-lg font-semibold">Bücher</h2><div className="divide-y">{!books.length && <p className="p-5 text-sm text-slate-500">Noch keine Bücher hochgeladen.</p>}{books.map(book => <Link key={book.book_id} href={`/workflow?book=${book.book_id}`} className="block p-5 hover:bg-slate-50"><p className="font-medium">{book.title || book.filename}</p><p className="mt-1 text-sm text-slate-500">{book.author}</p><p className="mt-2 text-xs text-slate-500">{book.chapter_count} Kapitel · Neuen Auftrag anlegen →</p></Link>)}</div></div></section>
  </main>;
}
