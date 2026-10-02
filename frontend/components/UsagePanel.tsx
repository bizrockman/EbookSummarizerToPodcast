import { UsageReport, numbers, dollars } from "@/lib/studio";

const phases: Record<string, string> = { reading: "Blockweise Kürzung", length_repair: "Längenkorrektur",
  translation: "Übersetzung", topic_map: "Kerngedanken sammeln", topic_reduce: "Themen zusammenführen",
  core_writing: "Kernfassung schreiben", core_length_repair: "Kernfassung korrigieren", audio: "Audio" };

export default function UsagePanel({ usage }: { usage: UsageReport }) {
  const totals = usage.totals;
  return <section className="panel p-5">
    <h2 className="text-lg font-semibold">Verbrauch dieses Auftrags</h2>
    <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div><p className="text-sm text-slate-500">Input-Tokens</p><p className="text-xl font-semibold">{numbers(totals.input)}</p></div>
      <div><p className="text-sm text-slate-500">Output-Tokens</p><p className="text-xl font-semibold">{numbers(totals.output)}</p></div>
      <div><p className="text-sm text-slate-500">Audio-Zeichen</p><p className="text-xl font-semibold">{numbers(totals.characters)}</p></div>
      <div><p className="text-sm text-slate-500">Kosten bisher, geschätzt</p><p className="text-xl font-semibold">{dollars(totals.known_cost_usd)}{totals.unknown_calls > 0 && " + offen"}</p></div>
    </div>
    {totals.unknown_calls > 0 && <p className="mt-3 text-sm text-amber-800">Bei {totals.unknown_calls} Aufrufen fehlt noch Verbrauch oder Preis. Die Kostensumme ist unvollständig.</p>}
    <details className="mt-4"><summary className="cursor-pointer text-sm text-slate-600">Token- und Kostendetails</summary>
      <p className="my-3 text-sm text-slate-500">{usage.note}</p>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b"><th className="p-2">Schritt</th><th className="p-2">Aufrufe</th><th className="p-2">Input</th><th className="p-2">Output</th><th className="p-2">USD, bekannt</th></tr></thead>
        <tbody>{usage.phases.map(p => <tr className="border-b" key={p.phase}><td className="p-2">{phases[p.phase] || p.phase}</td><td className="p-2">{p.calls}</td><td className="p-2">{numbers(p.input)}</td><td className="p-2">{numbers(p.output)}</td><td className="p-2">{dollars(p.known_cost_usd)}{p.unknown_calls > 0 && " + offen"}</td></tr>)}</tbody></table></div>
      <p className="mt-3 text-sm text-slate-500">Im Input enthalten: {numbers(totals.cached_input)} gelesene und {numbers(totals.cache_write || 0)} geschriebene Cache-Tokens. Im Output enthalten: {numbers(totals.reasoning)} Reasoning-Tokens. {totals.cache_hits} Schritte lokal wiederverwendet.</p>
      <details className="mt-3"><summary className="cursor-pointer text-sm">Einzelne API-Aufrufe und Modelle</summary><div className="mt-2 max-h-80 overflow-auto text-xs">{usage.calls.map(c => <p className="border-b py-2" key={c.id}>{phases[c.phase] || c.phase} · {c.provider}/{c.model} · {c.status} · Input {c.input ?? "unbekannt"} / Output {c.output ?? "unbekannt"} · {c.cost_usd === null ? "Preis offen" : dollars(c.cost_usd)}</p>)}</div></details>
    </details>
  </section>;
}
