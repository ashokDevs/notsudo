"use client";

import { useEffect, useState } from "react";
import { Github, Check, AlertCircle, LogOut, Bot, Save, Loader2, Trash2, ChevronDown } from "lucide-react";
import Image from "next/image";
import { authClient } from "@/lib/auth-client";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AIModel {
  id: string;
  name: string;
  provider: string;
}

export default function SettingsPage() {
  const { data: session } = authClient.useSession();
  const isConnected = !!session;

  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [customRules, setCustomRules] = useState<string>("");
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const router = useRouter();

  useEffect(() => {
    async function fetchModels(): Promise<void> {
      try {
        const res = await fetch(`${API_URL}/api/models`);
        if (res.ok) {
          const data = await res.json();
          setModels(data.models || []);
          if (!selectedModel && data.default) {
            setSelectedModel(data.default);
          }
        }
      } catch {
        // Silently fail - models will remain empty
      }
    }
    fetchModels();
  }, [selectedModel]);

  useEffect(() => {
    async function fetchSettings(): Promise<void> {
      if (!session?.user?.id) return;
      setLoadingSettings(true);
      try {
        const res = await fetch(`${API_URL}/api/user/ai-settings?user_id=${session.user.id}`);
        if (res.ok) {
          const data = await res.json();
          if (data.selectedModel) setSelectedModel(data.selectedModel);
          if (data.customRules) setCustomRules(data.customRules);
        }
      } finally {
        setLoadingSettings(false);
      }
    }
    fetchSettings();
  }, [session?.user?.id]);

  async function handleSaveSettings(): Promise<void> {
    if (!session?.user?.id) return;
    setSavingSettings(true);
    setSaveSuccess(false);
    try {
      const res = await fetch(`${API_URL}/api/user/ai-settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: session.user.id,
          selectedModel,
          customRules,
        }),
      });
      if (res.ok) {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3_000);
      }
    } finally {
      setSavingSettings(false);
    }
  }

  async function handleConnectGithub(): Promise<void> {
    await authClient.signIn.social({
      provider: "github",
      callbackURL: "/dashboard/settings"
    });
  }

  async function handleDisconnect(): Promise<void> {
    await authClient.signOut();
  }

  async function handleDeleteAccount(): Promise<void> {
    if (!session?.user?.id) return;

    const confirmed = window.confirm(
      "Are you absolutely sure? This will permanently delete your account, all subscriptions, repositories, and job history. This action cannot be undone."
    );

    if (!confirmed) return;

    setDeletingAccount(true);
    try {
      const res = await fetch(`${API_URL}/api/user/delete?user_id=${session.user.id}`, {
        method: "DELETE",
      });

      if (res.ok) {
        await authClient.signOut();
        router.push("/");
      } else {
        const errorData = await res.json();
        alert(errorData.error || "Failed to delete account");
      }
    } catch {
      alert("An error occurred while deleting your account");
    } finally {
      setDeletingAccount(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#020202] text-zinc-100 font-modern selection:bg-orange-500/30">
      {/* Main Content */}
      <main className="max-w-4xl mx-auto py-16 px-6">
        <div className="p-8 space-y-12">
          <div className="max-w-2xl space-y-12">
            {/* GitHub Connection */}
            <div className="modern-card overflow-hidden">
              <div className="px-8 py-6 border-b border-zinc-800/50">
                <h2 className="text-lg font-bold text-white tracking-tight">GitHub Connection</h2>
                <p className="text-sm text-zinc-500 mt-1 font-medium">
                  Connect your GitHub account to enable automated code reviews
                </p>
              </div>
              <div className="p-8">
                {isConnected ? (
                  <div className="flex flex-col gap-6">
                    <div className="flex items-center gap-5">
                      {session?.user?.image ? (
                        <Image
                          src={session.user.image}
                          alt={session.user.name || "User"}
                          width={56}
                          height={56}
                          className="rounded-2xl border border-zinc-800"
                        />
                      ) : (
                        <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                          <Check className="w-7 h-7 text-emerald-500" />
                        </div>
                      )}
                      <div>
                        <p className="font-bold text-zinc-100">
                          Connected as {session?.user?.name || "User"}
                        </p>
                        <p className="text-sm text-zinc-500 font-medium">
                           {session?.user?.email}
                        </p>
                      </div>
                    </div>

                    <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800/50">
                        <p className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-3">Granted Scopes</p>
                        <div className="flex flex-wrap gap-2">
                            <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-bold rounded border border-emerald-500/20">REPO</span>
                            <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-bold rounded border border-emerald-500/20">USER</span>
                            <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-bold rounded border border-emerald-500/20">READ:ORG</span>
                        </div>
                    </div>

                    <button
                        onClick={handleDisconnect}
                        className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-500 text-xs font-bold hover:bg-red-500/20 transition-all rounded-lg border border-red-500/20 w-fit"
                    >
                        <LogOut className="w-4 h-4" />
                        Disconnect Account
                    </button>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="flex items-start gap-4 p-5 bg-orange-500/5 border border-orange-500/10 rounded-xl">
                      <AlertCircle className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" />
                      <p className="text-sm text-zinc-400 font-medium leading-relaxed">
                        Connect your GitHub account to allow NotSudo to analyze your repositories and create pull requests.
                      </p>
                    </div>
                    <button
                      onClick={handleConnectGithub}
                      className="flex items-center gap-3 px-8 py-3 bg-white text-black font-bold text-sm hover:bg-zinc-200 transition-all rounded-xl active:scale-95"
                    >
                      <Github className="w-5 h-5" />
                      Connect to GitHub
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* AI Settings */}
            <div className="modern-card overflow-hidden">
              <div className="px-8 py-6 border-b border-zinc-800/50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-orange-600/10 flex items-center justify-center border border-orange-600/20">
                    <Bot className="w-5 h-5 text-orange-500" />
                  </div>
                  <h2 className="text-lg font-bold text-white tracking-tight">AI Agent Configuration</h2>
                </div>
                <p className="text-sm text-zinc-500 mt-1 font-medium">
                  Set your preferred model and define custom instructions for code generation
                </p>
              </div>
              <div className="p-8 space-y-8">
                {loadingSettings ? (
                  <div className="flex items-center gap-3 text-zinc-500 font-medium py-10">
                    <Loader2 className="w-5 h-5 animate-spin text-orange-500" />
                    <span>Pulling agent configuration...</span>
                  </div>
                ) : (
                  <>
                    <div className="space-y-3">
                      <label className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">
                        Intelligence Model
                      </label>
                      <div className="relative">
                        <select
                          value={selectedModel}
                          onChange={(e) => setSelectedModel(e.target.value)}
                          className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/10 transition-all appearance-none cursor-pointer"
                        >
                          {models.map((model) => (
                            <option key={model.id} value={model.id} className="bg-zinc-900">
                              {model.name} ({model.provider})
                            </option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-4 top-4 w-4 h-4 text-zinc-600 pointer-events-none" />
                      </div>
                    </div>

                    <div className="space-y-3">
                      <label className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">
                        Instruction Manual (Custom Rules)
                      </label>
                      <textarea
                        value={customRules}
                        onChange={(e) => setCustomRules(e.target.value)}
                        placeholder="Add custom instructions for the AI, e.g.:&#10;- Always use TypeScript&#10;- Follow eslint rules&#10;- Add JSDoc comments"
                        rows={6}
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-4 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/10 transition-all font-mono modern-scrollbar resize-none"
                      />
                    </div>

                    <div className="flex items-center gap-6 pt-4">
                      <button
                        onClick={handleSaveSettings}
                        disabled={savingSettings}
                        className="flex items-center gap-2 px-8 py-3 bg-orange-600 hover:bg-orange-700 text-white font-bold text-sm rounded-xl transition-all active:scale-95 disabled:opacity-50"
                      >
                        {savingSettings ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Save className="w-4 h-4" />
                        )}
                        Sync Changes
                      </button>
                      {saveSuccess && (
                        <div className="flex items-center gap-2 text-emerald-500 font-bold text-xs uppercase tracking-tight animate-in fade-in slide-in-from-left-2">
                          <Check className="w-4 h-4" />
                          Configuration Updated
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Danger Zone */}
            <div className="modern-card border-red-500/20 overflow-hidden">
              <div className="px-8 py-6 border-b border-red-500/10 bg-red-500/[0.02]">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center border border-red-500/20">
                    <Trash2 className="w-5 h-5 text-red-500" />
                  </div>
                  <h2 className="text-lg font-bold text-white tracking-tight">Danger Zone</h2>
                </div>
                <p className="text-sm text-zinc-500 mt-1 font-medium">
                  Irreversible actions for your account and data
                </p>
              </div>
              <div className="p-8">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-6 bg-red-500/5 border border-red-500/10 rounded-2xl">
                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-zinc-100">Delete Account</h3>
                    <p className="text-xs text-zinc-500 font-medium leading-relaxed max-w-md">
                      Permanently remove your account, subscriptions, and all associated data from our servers.
                    </p>
                  </div>
                  <button
                    onClick={handleDeleteAccount}
                    disabled={deletingAccount}
                    className="flex items-center justify-center gap-2 px-6 py-3 bg-red-500 hover:bg-red-600 text-white font-bold text-sm rounded-xl transition-all active:scale-95 disabled:opacity-50 whitespace-nowrap"
                  >
                    {deletingAccount ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    Delete Permanently
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
