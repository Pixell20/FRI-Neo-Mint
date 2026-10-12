import Link from "next/link";
import { Leaf, LineChart, Trophy, Sparkles } from "lucide-react";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 flex items-center gap-2 text-mint-700">
        <Leaf className="h-8 w-8" />
        <span className="text-3xl font-bold tracking-tight">NeoMint</span>
      </div>
      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Learn markets by playing them.</h1>
      <p className="mt-4 max-w-xl text-slate-600">
        Trade with virtual cash, climb the nightly leaderboard, and get AI feedback on your portfolio - zero real risk.
      </p>
      <div className="mt-8 flex gap-3">
        <Link href="/register" className="btn-primary">Start with $100,000</Link>
        <Link href="/login" className="btn-ghost">Log in</Link>
      </div>
      <div className="mt-14 grid w-full grid-cols-3 gap-4 text-sm text-slate-600">
        <div className="card"><LineChart className="mx-auto mb-2 h-5 w-5 text-mint-600" />Live-style quotes</div>
        <div className="card"><Trophy className="mx-auto mb-2 h-5 w-5 text-mint-600" />Daily leaderboard</div>
        <div className="card"><Sparkles className="mx-auto mb-2 h-5 w-5 text-mint-600" />AI insights</div>
      </div>
    </main>
  );
}
