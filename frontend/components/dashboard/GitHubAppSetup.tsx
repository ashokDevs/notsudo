"use client";

import { useEffect, useState } from 'react';
import { GitBranch, ExternalLink, Loader2, CheckCircle, AlertCircle, Download } from 'lucide-react';

interface GitHubAppStatus {
  configured: boolean;
  app_name?: string;
  app_slug?: string;
  install_url?: string;
  html_url?: string;
  error?: string;
  message?: string;
}

interface Installation {
  id: number;
  account: string;
  account_type: string;
  repository_selection: string;
  html_url: string;
  suspended_at: string | null;
}

interface Repo {
  id: string;
  name: string;
  full_name: string;
  private: boolean;
  html_url: string;
  description: string | null;
  language: string | null;
  default_branch: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function GitHubAppSetup() {
  const [status, setStatus] = useState<GitHubAppStatus | null>(null);
  const [installations, setInstallations] = useState<Installation[]>([]);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [selectedInstallation, setSelectedInstallation] = useState<number | null>(null);

  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    if (status?.configured) {
      fetchInstallations();
    }
  }, [status?.configured]);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/github-app/status`);
      const data = await res.json();
      setStatus(data);
    } catch {
      // Silently handle fetch errors - unconfigured state will be shown
    } finally {
      setLoading(false);
    }
  };

  const fetchInstallations = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/github-app/installations`);
      const data = await res.json();
      setInstallations(data.installations || []);

      if (data.installations?.length === 1) {
        setSelectedInstallation(data.installations[0].id);
        fetchRepos(data.installations[0].id);
      }
    } catch {
      // Silently handle fetch errors - empty installations will be shown
    }
  };

  const fetchRepos = async (installationId: number) => {
    setLoadingRepos(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/github-app/installations/${installationId}/repos`);
      const data = await res.json();
      setRepos(data.repos || []);
    } catch {
      // Silently handle fetch errors - empty repos will be shown
    } finally {
      setLoadingRepos(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
      </div>
    );
  }

  // GitHub App not configured
  if (!status?.configured) {
    return (
      <div className="border border-white/10 bg-black/50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertCircle className="w-5 h-5 text-yellow-500" />
          <h3 className="font-mono text-white font-bold">GitHub App Setup Required</h3>
        </div>
        <p className="font-mono text-sm text-gray-400 mb-4">
          {status?.message || 'GitHub App is not configured. The backend admin needs to set up the GitHub App credentials.'}
        </p>
        <p className="font-mono text-xs text-gray-500">
          Required environment variables: GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY
        </p>
      </div>
    );
  }

  // No installations yet
  if (installations.length === 0) {
    return (
      <div className="border border-white/10 bg-black/50 p-6 text-center">
        <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-4">
          <Download className="w-8 h-8 text-amber-500" />
        </div>
        <h3 className="font-mono text-white font-bold text-lg mb-2">
          Install {status.app_name || 'NotSudo'} GitHub App
        </h3>
        <p className="font-mono text-sm text-gray-400 mb-6 max-w-md mx-auto">
          Click below to install the GitHub App on your account or organization. 
          Select which repositories you want NotSudo to have access to.
        </p>
        <a
          href={status.install_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-6 py-3 bg-amber-500 text-black font-mono font-bold text-sm hover:bg-amber-400 transition-colors"
        >
          <GitBranch className="w-4 h-4" />
          Install GitHub App
          <ExternalLink className="w-4 h-4" />
        </a>
        <button
          onClick={fetchInstallations}
          className="block mx-auto mt-4 font-mono text-xs text-gray-500 hover:text-white transition-colors"
        >
          Already installed? Click to refresh
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Installation selector (if multiple) */}
      {installations.length > 1 && (
        <div className="border border-white/10 bg-black/50 p-4">
          <label className="font-mono text-xs uppercase tracking-wider text-gray-500 mb-2 block">
            Select Account
          </label>
          <div className="flex gap-2 flex-wrap">
            {installations.map((inst) => (
              <button
                key={inst.id}
                onClick={() => {
                  setSelectedInstallation(inst.id);
                  fetchRepos(inst.id);
                }}
                className={`px-4 py-2 font-mono text-sm border transition-colors ${
                  selectedInstallation === inst.id
                    ? 'bg-amber-500 text-black border-amber-500'
                    : 'bg-black/50 text-white border-white/10 hover:border-amber-500/50'
                }`}
              >
                {inst.account}
                {inst.suspended_at && (
                  <span className="ml-2 text-xs text-red-400">(suspended)</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Status banner */}
      <div className="flex items-center gap-3 p-4 border border-green-500/20 bg-green-500/5">
        <CheckCircle className="w-5 h-5 text-green-500" />
        <div>
          <p className="font-mono text-sm text-white">
            GitHub App installed on {installations.length} account{installations.length > 1 ? 's' : ''}
          </p>
          <p className="font-mono text-xs text-gray-400">
            NotSudo will automatically respond to @notsudo mentions in issues
          </p>
        </div>
        <a
          href={status.install_url}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto font-mono text-xs text-amber-500 hover:text-amber-400 flex items-center gap-1"
        >
          Manage <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* Repos list */}
      {selectedInstallation && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-mono text-xs uppercase tracking-wider text-gray-500">
              Connected Repositories ({repos.length})
            </h3>
            <button
              onClick={() => fetchRepos(selectedInstallation)}
              className="font-mono text-xs text-gray-500 hover:text-white transition-colors"
            >
              Refresh
            </button>
          </div>

          {loadingRepos ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="w-5 h-5 text-amber-500 animate-spin" />
            </div>
          ) : repos.length === 0 ? (
            <div className="border border-white/10 border-dashed bg-black/30 p-8 text-center">
              <p className="font-mono text-sm text-gray-400">
                No repositories found for this installation.
              </p>
              <a
                href={status.install_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 mt-2 font-mono text-xs text-amber-500 hover:text-amber-400"
              >
                Configure repository access <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {repos.map((repo) => (
                <div
                  key={repo.id}
                  className="relative border border-green-500/20 bg-green-500/5 p-5 hover:border-green-500/40 transition-colors group"
                >
                  {/* Active indicator */}
                  <div className="absolute top-3 right-3">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  </div>

                  <div className="flex items-center gap-2 mb-2">
                    <GitBranch className="w-4 h-4 text-gray-500" />
                    <span className="font-mono text-sm text-white font-medium truncate">
                      {repo.name}
                    </span>
                    {repo.private && (
                      <span className="px-1.5 py-0.5 text-[10px] bg-gray-800 text-gray-400 rounded">
                        Private
                      </span>
                    )}
                  </div>

                  {repo.description && (
                    <p className="font-mono text-xs text-gray-400 mb-3 line-clamp-2">
                      {repo.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between pt-3 border-t border-white/5">
                    {repo.language && (
                      <span className="font-mono text-xs text-gray-500">{repo.language}</span>
                    )}
                    <a
                      href={repo.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-xs text-gray-500 hover:text-amber-500 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!selectedInstallation && installations.length > 0 && (
        <p className="font-mono text-sm text-gray-400 text-center py-8">
          Select an account above to view connected repositories
        </p>
      )}
    </div>
  );
}
