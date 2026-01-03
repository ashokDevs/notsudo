"use client";

import { useEffect, useState, useMemo } from 'react';
import { Search, Loader2, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

interface Repo {
  full_name: string;
  name: string;
  owner: string;
  private: boolean;
  url: string;
  language: string | null;
  permissions: {
    admin: boolean;
  };
}

interface WebhookStatus {
  [key: string]: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function RepoList() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [webhookStatuses, setWebhookStatuses] = useState<WebhookStatus>({});
  const [loading, setLoading] = useState(true);
  const [checkingWebhooks, setCheckingWebhooks] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [processing, setProcessing] = useState<string | null>(null); // repo full_name being toggled
  const [bulkProcessing, setBulkProcessing] = useState(false);

  // Fetch repos on mount
  useEffect(() => {
    fetchRepos();
  }, []);

  // Fetch webhook statuses when repos are loaded
  useEffect(() => {
    if (repos.length > 0) {
      checkWebhooks(repos.map(r => r.full_name));
    }
  }, [repos]);

  const fetchRepos = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/api/repos`);
      if (!res.ok) throw new Error('Failed to fetch repositories');
      const data = await res.json();
      setRepos(data.repos || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const checkWebhooks = async (repoNames: string[]) => {
    try {
      setCheckingWebhooks(true);
      const res = await fetch(`${API_BASE_URL}/api/repos/check-webhooks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repos: repoNames }),
      });
      if (!res.ok) throw new Error('Failed to check webhooks');
      const data = await res.json();
      setWebhookStatuses(prev => ({ ...prev, ...data.statuses }));
    } catch (err: any) {
      console.error('Error checking webhooks:', err);
    } finally {
      setCheckingWebhooks(false);
    }
  };

  const toggleWebhook = async (repo: Repo) => {
    if (!repo.permissions.admin) return;

    const isEnabled = webhookStatuses[repo.full_name];
    const action = isEnabled ? 'disable' : 'enable';

    try {
      setProcessing(repo.full_name);
      const res = await fetch(`${API_BASE_URL}/api/repos/webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo: repo.full_name, action }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Failed to toggle webhook');
      }

      setWebhookStatuses(prev => ({
        ...prev,
        [repo.full_name]: !isEnabled
      }));
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setProcessing(null);
    }
  };

  const handleBulkAction = async (action: 'enable' | 'disable') => {
    const visibleRepos = filteredRepos.filter(r => r.permissions.admin);

    // Filter repos that actually need the action
    const reposToUpdate = visibleRepos.filter(repo => {
        const isEnabled = webhookStatuses[repo.full_name];
        if (action === 'enable') return !isEnabled;
        return isEnabled;
    }).map(r => r.full_name);

    if (reposToUpdate.length === 0) return;

    if (!confirm(`Are you sure you want to ${action} automation for ${reposToUpdate.length} repositories?`)) return;

    try {
        setBulkProcessing(true);
        const res = await fetch(`${API_BASE_URL}/api/repos/webhook/bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repos: reposToUpdate, action }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'Failed to perform bulk action');
        }

        const data = await res.json();

        // Update statuses based on results
        // Assuming backend returns { results: { repoName: boolean (success) } }
        // Or simpler, just re-check statuses or optimistically update.
        // Let's re-check statuses for accuracy.
        await checkWebhooks(visibleRepos.map(r => r.full_name));

    } catch (err: any) {
        alert(`Error: ${err.message}`);
    } finally {
        setBulkProcessing(false);
    }
  };

  const filteredRepos = useMemo(() => {
    return repos.filter(repo =>
      repo.full_name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [repos, searchQuery]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 flex items-center gap-2">
        <AlertCircle className="w-5 h-5" />
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-white/5 p-4 rounded-lg border border-white/10">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search repositories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-black/50 border border-white/10 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex gap-2">
           <button
            onClick={() => handleBulkAction('enable')}
            disabled={bulkProcessing}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {bulkProcessing ? 'Processing...' : 'Enable All'}
          </button>
          <button
            onClick={() => handleBulkAction('disable')}
            disabled={bulkProcessing}
            className="px-4 py-2 bg-red-900/50 hover:bg-red-900/70 text-red-200 border border-red-900/50 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {bulkProcessing ? 'Processing...' : 'Disable All'}
          </button>
        </div>
      </div>

      {/* Repo List */}
      <div className="grid gap-4">
        {filteredRepos.map(repo => {
          const isEnabled = webhookStatuses[repo.full_name];
          const isProcessing = processing === repo.full_name || bulkProcessing;
          const isAdmin = repo.permissions.admin;

          return (
            <div
              key={repo.full_name}
              className={`p-4 rounded-lg border transition-colors ${
                isEnabled
                  ? 'bg-blue-500/5 border-blue-500/20'
                  : 'bg-white/5 border-white/10'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-mono text-lg font-bold text-white">
                      {repo.full_name}
                    </h3>
                    {repo.private && (
                       <span className="px-2 py-0.5 text-xs bg-gray-700 text-gray-300 rounded-full">Private</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-1 line-clamp-1">
                    {repo.url}
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  {isEnabled ? (
                    <div className="flex items-center gap-1.5 text-green-400 text-sm font-medium">
                      <CheckCircle className="w-4 h-4" />
                      Active
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-gray-500 text-sm font-medium">
                      <XCircle className="w-4 h-4" />
                      Inactive
                    </div>
                  )}

                  <button
                    onClick={() => toggleWebhook(repo)}
                    disabled={!isAdmin || isProcessing}
                    className={`
                      relative w-12 h-6 rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                      ${isEnabled ? 'bg-blue-600' : 'bg-gray-600'}
                      ${(!isAdmin || isProcessing) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                    `}
                  >
                    <span
                      className={`
                        inline-block w-4 h-4 transform bg-white rounded-full transition-transform duration-200 ease-in-out mt-1 ml-1
                        ${isEnabled ? 'translate-x-6' : 'translate-x-0'}
                      `}
                    />
                  </button>
                </div>
              </div>
              {!isAdmin && (
                <p className="text-xs text-red-400 mt-2">
                  * Admin permissions required to enable automation
                </p>
              )}
            </div>
          );
        })}

        {filteredRepos.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No repositories found matching your search.
          </div>
        )}
      </div>
    </div>
  );
}
