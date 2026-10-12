"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Leaf } from "lucide-react";
import { api, setSession } from "@/lib/api";

export default function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = mode === "login" ? await api.login(email, password) : await api.register(email, password, name || "Trader");
      setSession(res.access_token, res.role);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <div className="flex items-center gap-2 text-mint-700">
          <Leaf className="h-6 w-6" /> <span className="text-xl font-bold">NeoMint</span>
        </div>
        <h1 className="text-lg font-semibold">{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        {mode === "register" && (
          <input className="input" placeholder="Display name" value={name} onChange={(e) => setName(e.target.value)} />
        )}
        <input className="input" type="email" required placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input className="input" type="password" required minLength={8} placeholder="Password (min 8 chars)" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Please wait..." : mode === "login" ? "Log in" : "Sign up"}</button>
        <p className="text-center text-sm text-slate-500">
          {mode === "login" ? (
            <>New here? <Link className="text-mint-700 underline" href="/register">Create an account</Link></>
          ) : (
            <>Have an account? <Link className="text-mint-700 underline" href="/login">Log in</Link></>
          )}
        </p>
      </form>
    </main>
  );
}
