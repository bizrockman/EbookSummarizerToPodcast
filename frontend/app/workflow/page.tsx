"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Book, getBooks, uploadEpub } from "@/lib/api";
import { createProduction, getStudioChapters, getStudioOptions, StudioChapter, StudioOptions, Strategy, numbers } from "@/lib/studio";

export default function WorkflowPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [bookId, setBookId] = useState("");
  const [chapters, setChapters] = useState<StudioChapter[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [options, setOptions] = useState<StudioOptions | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [strategy, setStrategy] = useState<Strategy>("reading");
  const [ratio, setRatio] = useState(40);
  const [coreWords, setCoreWords] = useState(1200);
  const [language, setLanguage] = useState("original");
  const [audio, setAudio] = useState(false);
  const [voice, setVoice] = useState("alloy");
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const sourceWords = chapters.filter(ch => selected.has(ch.href)).reduce((sum, ch) => sum + ch.word_count, 0);
  const targetWords = strategy === "reading" ? Math.round(sourceWords * ratio / 100) : strategy === "core" ? Math.min(sourceWords, coreWords) : sourceWords;

  useEffect(() => {
    let active = true;
    Promise.all([getBooks(), getStudioOptions()]).then(async ([list, config]) => {
      if (!active) return;
      setBooks(list); setOptions(config); setModel(config.text_model);
      const requested = new URLSearchParams(window.location.search).get("book");
      if (requested && list.some(b => b.book_id === requested)) await loadBook(requested);
    }).catch(e => active && setError(e instanceof Error ? e.message : String(e)));
    return () => { active = false; };
  }, []);

  async function loadBook(id: string) {
    setBusy("Lese Kapitel und Inhalt..."); setError(""); setChapters([]); setSelected(new Set()); setBookId(id);
    try {
      const result = await getStudioChapters(id);
      setChapters(result.chapters);
      setSelected(new Set(result.chapters.filter(ch => ch.selected).map(ch => ch.href)));
    } catch (e) { setError(e instanceof Error ? e.message : "Buch konnte nicht geladen werden"); }
    finally { setBusy(""); }
  }

  async function upload() {
    if (!file) return;
    setBusy("Lade EPUB hoch..."); setError("");
    try {
      const book = await uploadEpub(file);
      setBooks(previous => [book, ...previous.filter(b => b.book_id !== book.book_id)]);
      await loadBook(book.book_id);
      setFile(null);
    } catch (e) { setError(e instanceof Error ? e.message : "Upload fehlgeschlagen"); }
    finally { setBusy(""); }
  }

  async function create() {
    setBusy("Stelle Auftrag in die Warteschlange..."); setError("");
    try {
      const result = await createProduction({ book_id: bookId, chapters: Array.from(selected), strategy,
        ratio: ratio / 100, core_words: coreWords, language, audio, voice,
        text_provider: "openai", audio_provider: "openai", text_model: model || undefined });
      window.location.assign(`/productions/${result.job_id}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Auftrag fehlgeschlagen"); setBusy(""); }
  }

  return <main className="mx-auto max-w-5xl px-5 py-10">
    <Link href="/" className="text-sm text-slate-600">← Bibliothek und Aufträge</Link>
    <header className="my-8"><p className="text-xs uppercase tracking-[.2em] text-slate-500">Ebook Audio Studio</p>
      <h1 className="mt-2 text-3xl font-semibold">Dein Buch. Deine Lesetiefe.</h1>
      <p className="mt-3 max-w-2xl text-slate-600">Kapitel auswählen, eine passende Fassung erstellen und auf Wunsch übersetzen oder unterwegs hören.</p></header>
    <section className="panel mb-6 p-5"><h2 className="mb-4 text-lg font-semibold">1. Buch auswählen</h2>
      <div className="flex flex-wrap items-end gap-3"><label className="grow text-sm">EPUB-Datei<input type="file" accept=".epub" disabled={!!busy} onChange={e => setFile(e.target.files?.[0] || null)} className="mt-2 block w-full text-sm" /></label>
        <button disabled={!file || !!busy} onClick={upload} className="button-primary">Hochladen</button></div>
      {!!books.length && <label className="mt-5 block text-sm">Aus deiner Bibliothek<select value={bookId} disabled={!!busy} onChange={e => e.target.value && loadBook(e.target.value)} className="mt-2 w-full rounded-lg border p-2"><option value="">Buch auswählen</option>{books.map(book => <option key={book.book_id} value={book.book_id}>{book.title || book.filename}</option>)}</select></label>}
    </section>
    {!!chapters.length && <>
      <section className="panel mb-6 p-5"><h2 className="mb-4 text-lg font-semibold">2. Kapitel und Inhalt</h2>
        <div className="mb-3 flex flex-wrap gap-2"><button disabled={!!busy} onClick={() => setSelected(new Set(chapters.filter(ch => ch.word_count > 0).map(ch => ch.href)))} className="button-secondary">Alle mit Text</button>
          <button disabled={!!busy} onClick={() => setSelected(new Set())} className="button-secondary">Keine</button>
          <button disabled={!!busy} onClick={() => setSelected(new Set(chapters.filter(ch => ch.selected).map(ch => ch.href)))} className="button-secondary">Inhaltskapitel vorauswählen</button>
          <span className="self-center text-sm text-slate-500">{selected.size} von {chapters.length} · {numbers(sourceWords)} Wörter</span></div>
        <p className="mb-4 text-sm text-slate-500">Inhaltskapitel sind automatisch ausgewählt. Die Vorauswahl läuft lokal und ohne LLM-Kosten. Prüfe Zusatzmaterial und Anhänge anhand der Vorschau.</p>
        <div className="max-h-[28rem] overflow-auto rounded-xl border">{chapters.map(ch => <div key={ch.href} className="border-b p-3 last:border-0">
          <label className="flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1" disabled={!!busy || !ch.word_count} checked={selected.has(ch.href)} onChange={() => setSelected(previous => { const next = new Set(previous); if (next.has(ch.href)) next.delete(ch.href); else next.add(ch.href); return next; })} />
            <span className="min-w-0 grow"><span className="block font-medium">{ch.title}</span><span className="text-xs text-slate-500">{numbers(ch.word_count)} Wörter · {ch.selection_reason}</span></span></label>
          {!!ch.excerpt && <details className="ml-7 mt-2 text-sm"><summary className="cursor-pointer text-slate-500">Inhalt ansehen</summary><p className="mt-3 whitespace-pre-line leading-relaxed">{ch.excerpt}</p></details>}</div>)}</div>
      </section>
      <section className="panel mb-6 p-5"><h2 className="mb-4 text-lg font-semibold">3. Fassung und Länge</h2>
        <div className="grid gap-3 sm:grid-cols-3">{([
          { id: "reading", title: "Lesefassung", description: "Blockweise kürzen. Reihenfolge, Beispiele und Erzählton erhalten." },
          { id: "core", title: "Kernfassung", description: "Kerngedanken über Kapitel hinweg thematisch zusammenführen. Erste Version." },
          { id: "original", title: "Original", description: "Die ausgewählten Inhalte in voller Länge verwenden." }
        ] as const).map(item => <label key={item.id} className={`cursor-pointer rounded-xl border p-4 ${strategy === item.id ? "border-emerald-700 bg-emerald-50" : ""}`}><input type="radio" name="strategy" className="mr-2" disabled={!!busy} checked={strategy === item.id} onChange={() => setStrategy(item.id)} /><span className="font-medium">{item.title}</span><span className="mt-2 block text-sm text-slate-600">{item.description}</span></label>)}</div>
        {strategy === "reading" && <div className="mt-5"><label htmlFor="ratio" className="font-medium">Ziellänge: {ratio} % des Originals</label><input id="ratio" type="range" min="10" max="90" step="5" value={ratio} disabled={!!busy} onChange={e => setRatio(Number(e.target.value))} className="mt-3 w-full accent-emerald-700" /><div className="flex justify-between text-xs text-slate-500"><span>Stark verdichtet</span><span>Viel Tiefe</span></div><p className="mt-3 text-sm text-slate-500">Jede Länge entsteht aus dem Original. Die tatsächliche Länge kann abweichen.</p></div>}
        {strategy === "core" && <label className="mt-5 block text-sm">Ziellänge in Wörtern<select value={coreWords} disabled={!!busy} onChange={e => setCoreWords(Number(e.target.value))} className="ml-3 rounded-lg border p-2">{[300, 600, 1200, 2500, 5000].map(n => <option key={n} value={n}>{numbers(n)}</option>)}</select><span className="mt-3 block text-slate-500">Eine eigenständige Übersicht der zentralen Gedanken. Details und die ursprüngliche Gliederung können entfallen.</span></label>}
      </section>
      <section className="panel mb-6 p-5"><h2 className="mb-4 text-lg font-semibold">4. Übersetzung und Audio</h2>
        <label className="block text-sm">Sprache<select value={language} disabled={!!busy} onChange={e => setLanguage(e.target.value)} className="ml-3 rounded-lg border p-2">{[["original", "Originalsprache"], ["de", "Deutsch"], ["en", "Englisch"], ["fr", "Französisch"], ["es", "Spanisch"], ["it", "Italienisch"]].map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
        <label className="mt-5 flex items-center gap-3 text-sm"><input type="checkbox" checked={audio} disabled={!!busy || !options?.audio_available} onChange={e => setAudio(e.target.checked)} />Zusätzlich ein Hörbuch erstellen</label>
        {options && !options.audio_available && <p className="mt-2 text-sm text-amber-800">Audio benötigt eine lokale Installation von ffmpeg und ffprobe.</p>}
        {audio && <label className="mt-3 block text-sm">Stimme<select value={voice} disabled={!!busy} onChange={e => setVoice(e.target.value)} className="ml-3 rounded-lg border p-2">{options?.voices.map(v => <option key={v}>{v}</option>)}</select><span className="mt-2 block text-xs text-slate-500">Die Hörbuchstimme wird mit KI erzeugt.</span></label>}
        <details className="mt-5 text-sm"><summary className="cursor-pointer text-slate-500">Modelle und Anbieter</summary><p className="mt-3 text-slate-500">Text: OpenAI · Audio: OpenAI {options?.audio_model}. Weitere Anbieter lassen sich über eigene Adapter ergänzen.</p><label className="mt-3 block">Textmodell<input list="text-models" value={model} disabled={!!busy} maxLength={100} onChange={e => setModel(e.target.value)} className="ml-3 max-w-full rounded-lg border p-2" /></label><datalist id="text-models">{options?.suggested_text_models.map(m => <option key={m} value={m} />)}</datalist><p className="mt-2 text-xs text-slate-500">Verwende den exakten API-Modellnamen, etwa gpt-5 oder gpt-6.1-sol. Vor dem Start wird die Verfügbarkeit ohne Übertragung von Buchtext geprüft.</p></details>
      </section>
      <section className="panel p-5"><h2 className="font-semibold">Dein Auftrag</h2><p className="mt-2 text-sm text-slate-600">{selected.size} Kapitel · {numbers(sourceWords)} Wörter im Original · Ziel etwa {numbers(targetWords)} Wörter{language !== "original" && " vor der Übersetzung"}{audio && " · mit Hörbuch"}</p>
        <p className="mt-3 text-sm text-slate-500">{strategy === "original" && language === "original" && !audio ? "Dieser Originalexport braucht keinen kostenpflichtigen API-Aufruf. " : "Kürzung, Übersetzung und Audio nutzen kostenpflichtige APIs. Der tatsächliche Verbrauch wird pro Schritt erfasst. "}Du kannst mehrere Aufträge einstellen und später zurückkehren.</p>
        <button disabled={!!busy || !selected.size || !sourceWords || !options} onClick={create} className="button-primary mt-4">Auftrag starten</button></section>
    </>}
    {busy && <p role="status" className="mt-5 text-slate-600">{busy}</p>}
    {error && <p role="alert" className="mt-5 rounded-xl bg-rose-50 p-4 text-rose-800">{error}</p>}
  </main>;
}
