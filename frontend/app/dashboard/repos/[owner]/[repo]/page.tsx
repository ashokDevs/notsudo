"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Sidebar } from "@/components/dashboard/Sidebar";
import {
  GitBranch,
  Settings,
  AlertCircle,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronRight,
  ExternalLink,
  Copy
} from "lucide-react";

interface Issue {
  number: number;
  title: string;
  body: string;
  state: string;
  html_url: string;
  created_at: string;
  updated_at: string;
  user: {
    login: string;
    avatar_url: string;
  };
  labels: { name: string; color: string }[];
}

interface Job {
  id: string;
  repo: string;
  issueNumber: number;
  issueTitle: string;
  status: string;
  stage: string;
  createdAt: string;
  prUrl?: string;
  error?: string;
}

export default function RepositoryDetails() {
  const params = useParams();
  const repoFullName = `${params.owner}/${params.repo}`;
  const [activeTab, setActiveTab] = useState<"issues" | "jobs">("issues");
  const [showWebhookSetup, setShowWebhookSetup] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState<string>("");
  const [webhookSecret, setWebhookSecret] = useState<boolean>(false); // just checks if configured

  const [issues, setIssues] = useState<Issue[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch webhook URL and config
    fetch("http://localhost:8000/api/webhook-url")
      .then(res => res.json())
      .then(data => setWebhookUrl(data.webhookUrl))
      .catch(console.error);

    fetch("http://localhost:8000/api/config")
      .then(res => res.json())
      .then(data => setWebhookSecret(data.hasWebhookSecret))
      .catch(console.error);
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "issues") {
        const response = await fetch(`http://localhost:8000/api/repos/${repoFullName}/issues`);
        if (!response.ok) throw new Error("Failed to fetch issues");
        const data = await response.json();
        setIssues(data.issues);
      } else {
        const response = await fetch(`http://localhost:8000/api/jobs`);
        if (!response.ok) throw new Error("Failed to fetch jobs");
        const data = await response.json();
        // Filter jobs for this repo
        setJobs(data.filter((job: Job) => job.repo === repoFullName));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab, repoFullName]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // Could add toast notification here
  };

  return (
    <div className="min-h-screen bg-black">
      <Sidebar />

      <main className="ml-64 min-h-screen text-white">
        {/* Header */}
        <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 bg-black/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h1 className="font-mono text-xl font-bold">{repoFullName}</h1>
          </div>
          <button
            onClick={() => setShowWebhookSetup(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500/10 text-orange-500 hover:bg-orange-500/20 transition-colors font-mono text-sm border border-orange-500/20"
          >
            <Settings className="w-4 h-4" />
            Configure Webhook
          </button>
        </header>

        {/* Webhook Setup Modal */}
        {showWebhookSetup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-[#111] border border-white/10 rounded-xl p-6 max-w-2xl w-full shadow-2xl">
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-mono text-xl font-bold">Setup Webhook</h2>
                <button
                  onClick={() => setShowWebhookSetup(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-6 font-mono text-sm">
                <div className="space-y-2">
                  <p className="text-gray-400">1. Go to your repository settings:</p>
                  <a
                    href={`https://github.com/${repoFullName}/settings/hooks/new`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-blue-400 hover:underline"
                  >
                    Open Webhook Settings <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <div className="space-y-2">
                  <p className="text-gray-400">2. Set Payload URL to:</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-black border border-white/10 p-3 rounded text-green-400 font-mono">
                      {webhookUrl}
                    </code>
                    <button
                      onClick={() => copyToClipboard(webhookUrl)}
                      className="p-3 bg-white/5 border border-white/10 rounded hover:bg-white/10 transition-colors"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-gray-400">3. Set Content Type to:</p>
                  <code className="block w-fit bg-black border border-white/10 px-3 py-1 rounded text-orange-400">
                    application/json
                  </code>
                </div>

                {webhookSecret && (
                  <div className="space-y-2">
                    <p className="text-gray-400">4. Set Secret (from your .env):</p>
                    <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded text-yellow-500 text-xs">
                      Make sure to use the same secret defined in your backend environment variables.
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <p className="text-gray-400">5. Select events:</p>
                  <ul className="list-disc list-inside text-gray-500 pl-2 space-y-1">
                    <li>Issue comments</li>
                    <li>Issues</li>
                    <li>Pull requests</li>
                  </ul>
                </div>

                <div className="pt-4 flex justify-end">
                  <button
                    onClick={() => setShowWebhookSetup(false)}
                    className="px-6 py-2 bg-orange-500 hover:bg-orange-600 text-black font-bold rounded transition-colors"
                  >
                    Done
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="p-8">
          {/* Tabs */}
          <div className="flex items-center gap-6 mb-8 border-b border-white/10">
            <button
              onClick={() => setActiveTab("issues")}
              className={`pb-4 font-mono text-sm flex items-center gap-2 transition-colors relative ${
                activeTab === "issues" ? "text-white" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              <AlertCircle className="w-4 h-4" />
              Issues
              {activeTab === "issues" && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-500" />
              )}
            </button>
            <button
              onClick={() => setActiveTab("jobs")}
              className={`pb-4 font-mono text-sm flex items-center gap-2 transition-colors relative ${
                activeTab === "jobs" ? "text-white" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              <Play className="w-4 h-4" />
              Jobs
              {activeTab === "jobs" && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-500" />
              )}
            </button>
          </div>

          {/* Content */}
          <div className="max-w-4xl">
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-24 bg-white/5 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : error ? (
              <div className="border border-red-500/30 bg-red-500/5 rounded-lg p-4 text-center">
                <p className="font-mono text-red-400 text-sm">{error}</p>
                <button
                  onClick={fetchData}
                  className="mt-2 text-xs font-mono text-red-400 underline hover:text-red-300"
                >
                  Try again
                </button>
              </div>
            ) : activeTab === "issues" ? (
              <div className="space-y-4">
                {issues.length === 0 ? (
                  <div className="text-center py-12 text-gray-400 font-mono">
                    No open issues found.
                  </div>
                ) : (
                  issues.map((issue) => (
                    <div
                      key={issue.number}
                      className="group bg-white/5 border border-white/10 rounded-lg p-6 hover:border-orange-500/30 hover:bg-white/[0.07] transition-all"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2 flex-1">
                          <div className="flex items-center gap-3">
                            <h3 className="font-mono text-lg font-bold group-hover:text-orange-400 transition-colors">
                              {issue.title}
                            </h3>
                            <span className="text-xs font-mono text-gray-500">#{issue.number}</span>
                          </div>
                          <p className="font-mono text-sm text-gray-400 line-clamp-2">
                            {issue.body}
                          </p>
                          <div className="flex items-center gap-4 mt-4">
                            <div className="flex items-center gap-2 text-xs font-mono text-gray-500">
                              <img
                                src={issue.user.avatar_url}
                                alt={issue.user.login}
                                className="w-5 h-5 rounded-full"
                              />
                              {issue.user.login}
                            </div>
                            <span className="text-xs font-mono text-gray-600">
                              Opened {new Date(issue.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <a
                          href={issue.html_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 text-gray-500 hover:text-white transition-colors"
                        >
                          <ExternalLink className="w-5 h-5" />
                        </a>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {jobs.length === 0 ? (
                  <div className="text-center py-12 text-gray-400 font-mono">
                    No jobs found for this repository.
                  </div>
                ) : (
                  jobs.map((job) => (
                    <div
                      key={job.id}
                      className="bg-white/5 border border-white/10 rounded-lg p-6"
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <StatusIcon status={job.status} />
                          <span className="font-mono text-sm text-white capitalize">
                            {job.status}
                          </span>
                        </div>
                        <span className="font-mono text-xs text-gray-500">
                          {new Date(job.createdAt).toLocaleString()}
                        </span>
                      </div>

                      <div className="space-y-1 mb-4">
                        <h3 className="font-mono font-bold text-white">
                          Issue #{job.issueNumber}: {job.issueTitle}
                        </h3>
                        <p className="font-mono text-sm text-gray-400">
                          Stage: {job.stage}
                        </p>
                      </div>

                      {job.prUrl && (
                        <a
                          href={job.prUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 text-sm font-mono text-blue-400 hover:underline"
                        >
                          View Pull Request <ExternalLink className="w-3 h-3" />
                        </a>
                      )}

                      {job.error && (
                        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-red-400 font-mono text-sm">
                          {job.error}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    case 'failed':
      return <XCircle className="w-5 h-5 text-red-500" />;
    case 'processing':
      return <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
    default:
      return <Clock className="w-5 h-5 text-gray-500" />;
  }
}
