"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { GitBranch, Lock, Search, RefreshCw, ChevronDown, AlertCircle } from "lucide-react";
import { useSession } from "@/lib/auth-client";

interface Repository {
  full_name: string;
  name: string;
  owner: string;
  private: boolean;
  description: string | null;
  url: string;
  language: string | null;
  updated_at: string | null;
  permissions: {
    admin: boolean;
    push: boolean;
    pull: boolean;
  };
}

export default function Repositories() {
  const router = useRouter();
  const { data: session, isPending } = useSession();
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchRepos = useCallback(async (): Promise<void> => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/api/repos`);
      if (!response.ok) {
        throw new Error("Failed to fetch repositories");
      }
      const data = await response.json();
      setRepos(data.repos);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRepos();
  }, [fetchRepos]);

  const filteredRepos = repos.filter((repo) =>
    repo.full_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isPending) {
    return (
      <div className="min-h-screen bg-[#020202] flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!session) return null;

  return (
    <div className="min-h-screen bg-[#020202] text-zinc-100 font-modern selection:bg-orange-500/30">
      <main className="max-w-4xl mx-auto py-16 px-6">
        <div className="space-y-8">
          {/* Header & Search */}
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-zinc-100 uppercase tracking-tight">Browse Cloud Repositories</h2>
              <button
                onClick={fetchRepos}
                className="p-2 hover:bg-zinc-800 rounded-lg transition-all text-zinc-500 hover:text-white"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>

            <div className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 group-focus-within:text-orange-500 transition-colors" />
              <input
                type="text"
                placeholder="Find in your stack..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-zinc-900/50 border border-zinc-800 rounded-xl pl-12 pr-6 py-4 text-sm text-zinc-100 focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/10 transition-all font-medium"
              />
            </div>
          </div>

          {/* Error State */}
          {error && (
            <div className="modern-card p-10 text-center flex flex-col items-center gap-4">
              <AlertCircle className="w-10 h-10 text-red-500/50" />
              <p className="text-zinc-400 font-medium">{error}</p>
              <button
                onClick={fetchRepos}
                className="text-xs font-bold text-orange-500 hover:text-orange-400 uppercase tracking-widest"
              >
                Retry handshake
              </button>
            </div>
          )}

          {/* Repo List */}
          <div className="space-y-4">
            {loading && !repos.length ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-24 bg-zinc-900/50 border border-zinc-800 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : filteredRepos.length === 0 ? (
              <div className="bg-zinc-900/10 border-2 border-dashed border-zinc-800/50 p-16 rounded-[2rem] text-center">
                <p className="text-zinc-600 font-bold uppercase tracking-widest">No matching repositories</p>
              </div>
            ) : (
              filteredRepos.map((repo) => (
                <div
                  key={repo.full_name}
                  onClick={() => router.push(`/dashboard/repos/${repo.full_name}`)}
                  className="group modern-card p-6 flex items-center justify-between hover:border-orange-500/30 transition-all cursor-pointer relative overflow-hidden"
                >
                  <div className="flex items-center gap-5 relative z-10 flex-1 min-w-0">
                    <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center group-hover:bg-orange-500/5 group-hover:border-orange-500/20 transition-all shrink-0">
                      <GitBranch className="w-6 h-6 text-zinc-600 group-hover:text-orange-500/60" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-sm font-bold text-zinc-100 truncate group-hover:text-orange-400 transition-colors">
                          {repo.name}
                        </h3>
                        {repo.private && (
                          <span className="flex items-center gap-1.5 px-2 py-0.5 bg-zinc-800 text-zinc-500 text-[9px] font-bold rounded-md border border-zinc-700">
                            <Lock className="w-2.5 h-2.5" /> PRIVATE
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest mb-2">
                        {repo.owner}
                      </p>
                      {repo.description && (
                         <p className="text-xs text-zinc-500 font-medium truncate mb-1">
                           {repo.description}
                         </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-4 pl-6 relative z-10">
                     <div className="hidden sm:flex flex-col items-end gap-1 text-[9px] font-bold text-zinc-700 uppercase tracking-tighter">
                        <span>Updated</span>
                        <span className="text-zinc-500">{repo.updated_at ? new Date(repo.updated_at).toLocaleDateString() : "Never"}</span>
                     </div>
                     <ChevronDown className="w-4 h-4 text-zinc-800 -rotate-90 group-hover:text-orange-500 transition-colors" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
