"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, FileText, Leaf, LogOut, Sparkles, Trophy } from "lucide-react";
import {
  AIAnalysis, HistoryPoint, LeaderRow, Portfolio, Quote,
  api, clearSession, downloadPdf,
} from "@/lib/api";

const money = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const pct = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;

export default function Dashboard() {
  const router = useRouter();
  const [stocks, setStocks] = useState<Quote[]>([]);
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [leaders, setLeaders] = useState<LeaderRow[]>([]);
  const [ai, setAi] = useState<AIAnalysis | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [symbol, setSymbol] = useState("AAPL");
  const [shares, setShares] = useState(1);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [lastTx, setLastTx] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, p, h, l] = await Promise.all([api.stocks(), api.portfolio(), api.history(), api.leaderboard()]);
      setStocks(s); setPf(p); setHistory(h); setLeaders(l);
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Failed to load" });
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 20_000);
    return () => clearInterval(id);
  }, [refresh]);

  async function trade(side: "buy" | "sell") {
    setMsg(null);
    try {
      const r = await api.trade(side, symbol, shares);
      setLastTx(r.transaction_id);
      setMsg({ ok: true, text: `${r.type} ${r.shares} ${r.symbol} @ ${money(r.price)} = ${money(r.total)}` });
      refresh();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Trade failed" });
    }
  }

  async function runAi() {
    setAiBusy(true);
    try { setAi(await api.analyze()); } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "AI analysis failed" });
    } finally { setAiBusy(false); }
  }

  function logout() { clearSession(); router.push("/login"); }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-mint-700"><Leaf className="h-6 w-6" /><span className="text-xl font-bold">NeoMint</span></div>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={() => downloadPdf("/api/reports/weekly-statement", "neomint-weekly-statement.pdf")}>
            <FileText className="h-4 w-4" /> Weekly statement
          </button>
          <button className="btn-ghost" onClick={logout}><LogOut className="h-4 w-4" /> Log out</button>
        </div>
      </header>

      <section className="grid gap-4 sm:grid-cols-4">
        {[
          ["Net worth", pf ? money(pf.net_worth) : "-"],
          ["Cash", pf ? money(pf.cash) : "-"],
          ["Invested", pf ? money(pf.holdings_value) : "-"],
          ["Total return", pf ? pct(pf.total_return_pct) : "-"],
        ].map(([k, v]) => (
          <div key={k} className="card"><p className="text-xs uppercase tracking-wide text-slate-500">{k}</p><p className="mt-1 text-2xl font-semibold">{v}</p></div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <h2 className="mb-3 font-semibold">Net worth history</h2>
          {history.length < 2 ? (
            <p className="py-10 text-center text-sm text-slate-500">History appears after the first nightly close (admins can trigger it manually).</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={history}>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} width={70} />
                <Tooltip formatter={(v: number) => money(v)} />
                <Area dataKey="net_worth" stroke="#059669" fill="#10b98133" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card space-y-3">
          <h2 className="font-semibold">Place a trade</h2>
          <select className="input" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {stocks.map((s) => <option key={s.symbol} value={s.symbol}>{s.symbol} - {s.name}</option>)}
          </select>
          <input className="input" type="number" min={1} value={shares} onChange={(e) => setShares(Math.max(1, Number(e.target.value)))} />
          <div className="flex gap-2">
            <button className="btn-primary flex-1" onClick={() => trade("buy")}>Buy</button>
            <button className="btn-ghost flex-1" onClick={() => trade("sell")}>Sell</button>
          </div>
          {msg && <p className={`text-sm ${msg.ok ? "text-mint-700" : "text-red-600"}`} role="status">{msg.text}</p>}
          {lastTx && (
            <button className="text-sm text-mint-700 underline" onClick={() => downloadPdf(`/api/reports/trade-slip/${lastTx}`, `trade-slip-${lastTx}.pdf`)}>
              Download confirmation slip
            </button>
          )}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card overflow-x-auto">
          <h2 className="mb-3 font-semibold">Market</h2>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500"><tr><th>Symbol</th><th className="text-right">Price</th><th className="text-right">Change</th></tr></thead>
            <tbody>
              {stocks.map((s) => (
                <tr key={s.symbol} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50" onClick={() => setSymbol(s.symbol)}>
                  <td className="py-2 font-medium">{s.symbol}<span className="ml-2 text-xs text-slate-400">{s.name}</span></td>
                  <td className="text-right">{money(s.price)}</td>
                  <td className={`text-right ${s.change >= 0 ? "text-mint-600" : "text-red-600"}`}>
                    {s.change >= 0 ? <ArrowUpRight className="inline h-3 w-3" /> : <ArrowDownRight className="inline h-3 w-3" />} {pct(s.change_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card overflow-x-auto">
          <h2 className="mb-3 font-semibold">Your holdings</h2>
          {pf && pf.holdings.length === 0 ? <p className="py-6 text-center text-sm text-slate-500">No positions yet - place your first trade.</p> : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-slate-500"><tr><th>Symbol</th><th className="text-right">Qty</th><th className="text-right">Value</th><th className="text-right">P&amp;L</th></tr></thead>
              <tbody>
                {pf?.holdings.map((h) => (
                  <tr key={h.symbol} className="border-t border-slate-100">
                    <td className="py-2 font-medium">{h.symbol}</td>
                    <td className="text-right">{h.quantity}</td>
                    <td className="text-right">{money(h.market_value)}</td>
                    <td className={`text-right ${h.unrealized_pnl >= 0 ? "text-mint-600" : "text-red-600"}`}>{pct(h.unrealized_pnl_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 font-semibold"><Sparkles className="h-4 w-4 text-mint-600" /> AI portfolio insights</h2>
            <button className="btn-primary" onClick={runAi} disabled={aiBusy}>{aiBusy ? "Analyzing..." : "Analyze"}</button>
          </div>
          {ai ? (
            <div className="space-y-2 text-sm">
              <p>{ai.summary}</p>
              <p><b>Risk score:</b> {ai.risk_score}/100 &middot; <b>Diversification:</b> {ai.diversification}</p>
              <ul className="list-disc space-y-1 pl-5">{ai.suggestions.map((s, i) => <li key={i}>{s}</li>)}</ul>
              <p className="text-xs text-slate-400">Educational only, not investment advice. Source: {ai.source}</p>
            </div>
          ) : <p className="text-sm text-slate-500">Get a plain-English review of your allocation and risk.</p>}
        </div>

        <div className="card">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><Trophy className="h-4 w-4 text-amber-500" /> Leaderboard</h2>
          {leaders.length === 0 ? <p className="text-sm text-slate-500">Rankings appear after the nightly close.</p> : (
            <ol className="space-y-1 text-sm">
              {leaders.slice(0, 10).map((r) => (
                <li key={r.rank} className="flex justify-between border-t border-slate-100 py-1.5">
                  <span>#{r.rank} {r.display_name}</span><span>{money(r.net_worth)} <span className="text-slate-400">({pct(r.daily_return_pct)})</span></span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </section>
    </div>
  );
}
