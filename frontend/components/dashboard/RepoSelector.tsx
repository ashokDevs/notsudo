"use client";

import React, { useState, useEffect } from "react";
import { GitBranch, ChevronDown, Search, Loader2, Check, RefreshCw, X } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Repo {
  full_name: string;
  name: string;
  private: boolean;
}

interface Installation {
  id: number;
  account: string;
}

interface RepoSelectorProps {
  onSelect: (repoFullName: string) => void;
  selectedRepo: string | null;
}

export default function RepoSelector({ onSelect, selectedRepo }: RepoSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [installUrl, setInstallUrl] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && repos.length === 0) {
      fetchRepos();
    }
  }, [isOpen]);

  const fetchRepos = async () => {
    setLoading(true);
    try {
      const statusRes = await fetch(`${API_BASE_URL}/api/github-app/status`);
      const statusData = await statusRes.json();
      if (statusData.install_url) {
        setInstallUrl(statusData.install_url);
      }

      const installRes = await fetch(`${API_BASE_URL}/api/github-app/installations`);
      const installData = await installRes.json();
      const installations: Installation[] = installData.installations || [];

      const allRepos: Repo[] = [];
      for (const inst of installations) {
        const repoRes = await fetch(`${API_BASE_URL}/api/github-app/installations/${inst.id}/repos`);
        const repoData = await repoRes.json();
        const reposFromInstall = (repoData.repos || []).map((r: { full_name: string; name: string; private: boolean }) => ({
          full_name: r.full_name,
          name: r.name,
          private: r.private
        }));
        allRepos.push(...reposFromInstall);
      }
      setRepos(allRepos);
    } catch {
      // Silently handle fetch errors - user will see "No repositories found"
    } finally {
      setLoading(false);
    }
  };

  const filteredRepos = repos.filter(repo =>
    repo.full_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/50 border border-zinc-800 rounded-lg hover:bg-zinc-800 transition-all group min-w-[160px]"
      >
        <div className="w-5 h-5 rounded bg-orange-500/10 flex items-center justify-center border border-orange-500/20 text-orange-500">
          <GitBranch className="w-3.5 h-3.5" />
        </div>
        <span className="text-sm font-medium text-zinc-300 truncate text-left flex-1">
          {selectedRepo || "Select repository"}
        </span>
        <ChevronDown className={cn("w-4 h-4 text-zinc-500 transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 mt-2 w-80 bg-[#121214] border border-zinc-800/80 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
            {/* Search Header */}
            <div className="p-3">
              <div className="relative flex items-center bg-zinc-900/50 border border-zinc-800/50 rounded-lg px-3 py-2 group focus-within:border-orange-500/40 transition-colors">
                <Search className="w-4 h-4 text-zinc-500 mr-2" />
                <input
                  autoFocus
                  type="text"
                  placeholder="Choose a repo"
                  className="w-full bg-transparent border-none focus:outline-none focus:ring-0 text-sm p-0 text-zinc-200 placeholder:text-zinc-600"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            {/* repo list */}
            <div className="max-h-72 overflow-y-auto px-2 pb-2 modern-scrollbar">
              {loading ? (
                <div className="p-12 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="w-5 h-5 text-orange-500 animate-spin" />
                  <span className="text-xs text-zinc-500">Fetching your repositories...</span>
                </div>
              ) : filteredRepos.length > 0 ? (
                <div className="space-y-0.5">
                  {filteredRepos.map(repo => (
                    <button
                      key={repo.full_name}
                      className={cn(
                        "w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-all text-left",
                        selectedRepo === repo.full_name
                          ? "text-zinc-100"
                          : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100"
                      )}
                      onClick={() => {
                        onSelect(repo.full_name);
                        setIsOpen(false);
                      }}
                    >
                      <span className="truncate">{repo.full_name}</span>
                      {selectedRepo === repo.full_name && (
                        <Check className="w-4 h-4 text-zinc-100 flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-zinc-600 font-medium">
                  No repositories found
                </div>
              )}
            </div>

            {/* footer actions */}
            <div className="border-t border-zinc-800/50 p-2 space-y-0.5">
              {installUrl && (
                <a 
                  href={installUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100 rounded-lg text-sm transition-all text-left"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Configure repo access</span>
                </a>
              )}
              <button className="w-full flex items-center gap-3 px-3 py-2.5 text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100 rounded-lg text-sm transition-all text-left">
                <X className="w-4 h-4" />
                <span>Detach repo</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
