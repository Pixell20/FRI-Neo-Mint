const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getToken(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem("neomint_token");
}

export function setSession(token: string, role: string) {
  localStorage.setItem("neomint_token", token);
  localStorage.setItem("neomint_role", role);
  // Presence cookie lets middleware gate routes; the API still verifies the JWT on every call.
  document.cookie = `neomint_session=1; path=/; max-age=${60 * 60}; samesite=lax`;
}

export function clearSession() {
  localStorage.removeItem("neomint_token");
  localStorage.removeItem("neomint_role");
  document.cookie = "neomint_session=; path=/; max-age=0";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth/")) {
    clearSession();
    window.location.href = "/login";
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function downloadPdf(path: string, filename: string) {
  const res = await fetch(`${BASE}${path}`, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) throw new Error("Could not generate PDF");
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export type Quote = { symbol: string; name: string; price: number; change: number; change_pct: number; day_high: number; day_low: number };
export type Holding = { symbol: string; quantity: number; avg_buy_price: number; current_price: number; market_value: number; unrealized_pnl: number; unrealized_pnl_pct: number };
export type Portfolio = { cash: number; holdings_value: number; net_worth: number; total_return_pct: number; holdings: Holding[] };
export type TradeResult = { transaction_id: number; symbol: string; type: string; shares: number; price: number; total: number; cash_balance: number };
export type AIAnalysis = { summary: string; risk_score: number; diversification: string; suggestions: string[]; source: string };
export type LeaderRow = { rank: number; display_name: string; net_worth: number; daily_return_pct: number };
export type HistoryPoint = { date: string; net_worth: number };

export const api = {
  register: (email: string, password: string, display_name: string) =>
    request<{ access_token: string; role: string }>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password, display_name }) }),
  login: (email: string, password: string) =>
    request<{ access_token: string; role: string }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  stocks: () => request<Quote[]>("/api/market/stocks"),
  portfolio: () => request<Portfolio>("/api/portfolio"),
  history: () => request<HistoryPoint[]>("/api/portfolio/history"),
  leaderboard: () => request<LeaderRow[]>("/api/leaderboard"),
  trade: (side: "buy" | "sell", symbol: string, shares: number) =>
    request<TradeResult>(`/api/trade/${side}`, { method: "POST", body: JSON.stringify({ symbol, shares }) }),
  analyze: () => request<AIAnalysis>("/api/ai/analyze-portfolio", { method: "POST" }),
};
