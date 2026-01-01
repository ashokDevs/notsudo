"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { GitBranch, Lock, Search, RefreshCw } from "lucide-react";

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
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchRepos = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("http://localhost:8000/api/repos");
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
  };

  useEffect(() => {
    fetchRepos();
  }, []);

  const filteredRepos = repos.filter((repo) =>
    repo.full_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-black">
      <Sidebar />

      <main className="ml-64 min-h-screen text-white">
        <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 bg-black/50 backdrop-blur-sm sticky top-0 z-10">
          <h1 className="font-mono text-xl font-bold">Repositories</h1>
          <button
            onClick={fetchRepos}
            className="p-2 hover:bg-white/10 rounded-full transition-colors"
            title="Refresh repositories"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </header>

        <div className="p-8">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search repositories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-3 font-mono text-sm text-white focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50"
              />
            </div>

            {/* Error State */}
            {error && (
              <div className="border border-red-500/30 bg-red-500/5 rounded-lg p-4 text-center">
                <p className="font-mono text-red-400 text-sm">{error}</p>
                <button
                  onClick={fetchRepos}
                  className="mt-2 text-xs font-mono text-red-400 underline hover:text-red-300"
                >
                  Try again
                </button>
              </div>
            )}

            {/* Loading State */}
            {loading && !repos.length && (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-24 bg-white/5 rounded-lg animate-pulse" />
                ))}
              </div>
            )}

            {/* Empty State */}
            {!loading && filteredRepos.length === 0 && (
              <div className="text-center py-12">
                <p className="font-mono text-gray-400">No repositories found</p>
              </div>
            )}

            {/* Repo List */}
            <div className="space-y-4">
              {filteredRepos.map((repo) => (
                <div
                  key={repo.full_name}
                  onClick={() => router.push(`/dashboard/repos/${repo.full_name}`)}
                  className="group bg-white/5 border border-white/10 rounded-lg p-6 hover:border-orange-500/30 hover:bg-white/[0.07] transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <h3 className="font-mono text-lg font-bold group-hover:text-orange-400 transition-colors">
                          {repo.full_name}
                        </h3>
                        {repo.private && (
                          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/10 text-xs font-mono text-gray-400">
                            <Lock className="w-3 h-3" />
                            Private
                          </div>
                        )}
                      </div>
                      {repo.description && (
                        <p className="font-mono text-sm text-gray-400 line-clamp-2">
                          {repo.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-xs font-mono text-gray-500">
                        {repo.language && (
                          <div className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-orange-500" />
                            {repo.language}
                          </div>
                        )}
                        {repo.updated_at && (
                          <span>Updated {new Date(repo.updated_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <GitBranch className="w-5 h-5 text-gray-500 group-hover:text-orange-500 transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
