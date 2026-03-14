"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
  Loader2
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const [issues, setIssues] = useState<Issue[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "issues") {
        const response = await fetch(`${API_URL}/api/repos/${repoFullName}/issues`);
        if (!response.ok) throw new Error("Failed to fetch issues");
        const data = await response.json();
        setIssues(data.issues);
      } else {
        const response = await fetch(`${API_URL}/api/jobs`);
        if (!response.ok) throw new Error("Failed to fetch jobs");
        const data = await response.json();
        setJobs(data.filter((job: Job) => job.repo === repoFullName));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred");
    } finally {
      setLoading(false);
    }
  }, [activeTab, repoFullName]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="min-h-screen bg-[#020202] text-zinc-100 font-modern selection:bg-orange-500/30">
      <main className="max-w-4xl mx-auto py-16 px-6">
        {/* Modern Tabs */}
        <div className="flex items-center gap-10 mb-10 border-b border-zinc-800/50">
          <button
            onClick={() => setActiveTab("issues")}
            className={cn(
              "pb-4 text-sm font-bold uppercase tracking-widest transition-all relative",
              activeTab === "issues" ? "text-white" : "text-zinc-600 hover:text-zinc-400"
            )}
          >
            Issues
            {activeTab === "issues" && (
              <div className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-orange-600 rounded-full" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("jobs")}
            className={cn(
              "pb-4 text-sm font-bold uppercase tracking-widest transition-all relative",
              activeTab === "jobs" ? "text-white" : "text-zinc-600 hover:text-zinc-400"
            )}
          >
            Job History
            {activeTab === "jobs" && (
              <div className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-orange-600 rounded-full" />
            )}
          </button>
        </div>

        {/* Dynamic Content */}
        <div className="space-y-6">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-24 bg-zinc-900/50 border border-zinc-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : error ? (
            <div className="modern-card p-10 text-center flex flex-col items-center gap-4">
              <AlertCircle className="w-10 h-10 text-red-500/50" />
              <p className="text-zinc-400 font-medium">{error}</p>
              <button
                onClick={fetchData}
                className="text-xs font-bold text-orange-500 hover:text-orange-400 uppercase tracking-widest"
              >
                Retry handshake
              </button>
            </div>
          ) : activeTab === "issues" ? (
            <div className="space-y-4">
              {issues.length === 0 ? (
                <div className="bg-zinc-900/10 border-2 border-dashed border-zinc-800/50 p-16 rounded-[2rem] text-center">
                  <p className="text-zinc-600 font-bold uppercase tracking-widest">No open issues detected</p>
                </div>
              ) : (
                issues.map((issue) => (
                  <div
                    key={issue.number}
                    className="group modern-card p-6 flex flex-col justify-between hover:border-orange-500/30 transition-all cursor-pointer relative"
                  >
                    <div className="flex items-start justify-between gap-6">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                           <span className="text-[10px] font-bold text-zinc-600 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded">#{issue.number}</span>
                           <h3 className="text-sm font-bold text-zinc-100 truncate group-hover:text-orange-400 transition-colors">
                            {issue.title}
                          </h3>
                        </div>
                        <p className="text-xs text-zinc-500 font-medium line-clamp-2 leading-relaxed">
                          {issue.body || "No description provided."}
                        </p>
                        
                        <div className="flex items-center gap-4 mt-6">
                           <div className="flex items-center gap-2">
                              <Image src={issue.user.avatar_url} width={20} height={20} className="rounded-full border border-zinc-800" alt={issue.user.login} />
                              <span className="text-[10px] font-bold text-zinc-600 uppercase">{issue.user.login}</span>
                           </div>
                           <div className="w-1 h-1 bg-zinc-800 rounded-full" />
                           <span className="text-[10px] font-bold text-zinc-700 uppercase">{new Date(issue.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <a
                        href={issue.html_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 bg-zinc-900 rounded-lg border border-zinc-800 text-zinc-600 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {jobs.length === 0 ? (
                <div className="bg-zinc-900/10 border-2 border-dashed border-zinc-800/50 p-16 rounded-[2rem] text-center">
                  <p className="text-zinc-600 font-bold uppercase tracking-widest">No job history available</p>
                </div>
              ) : (
                jobs.map((job) => (
                  <div
                    key={job.id}
                    className="group modern-card p-6 hover:border-orange-500/30 transition-all cursor-pointer"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <StatusIcon status={job.status} />
                        <span className="text-[10px] font-bold text-zinc-100 uppercase tracking-widest">
                          {job.status}
                        </span>
                      </div>
                      <span className="text-[10px] font-bold text-zinc-600 uppercase">
                        {new Date(job.createdAt).toLocaleString()}
                      </span>
                    </div>

                    <div className="mb-6">
                      <h3 className="text-sm font-bold text-zinc-100 mb-1">
                        Issue #{job.issueNumber}: {job.issueTitle}
                      </h3>
                      <p className="text-xs text-zinc-500 font-medium uppercase tracking-tighter">
                        Current stage: <span className="text-orange-500/80">{job.stage}</span>
                      </p>
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-zinc-800/50">
                      {job.prUrl ? (
                        <a
                          href={job.prUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-[10px] font-bold text-orange-500 hover:text-orange-400 uppercase tracking-widest transition-all"
                        >
                          View Pull Request <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : <div />}
                      
                      <Link href={`/jobs/${job.id}`} className="text-[10px] font-bold text-zinc-600 hover:text-zinc-300 uppercase tracking-widest transition-all">
                        Full session log →
                      </Link>
                    </div>

                    {job.error && (
                      <div className="mt-4 p-4 bg-red-500/5 border border-red-500/10 rounded-xl text-red-500 text-[10px] font-bold uppercase tracking-tight">
                        {job.error}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <div className="w-5 h-5 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 text-emerald-500"><CheckCircle2 className="w-3 h-3" /></div>;
    case 'failed':
      return <div className="w-5 h-5 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20 text-red-500"><XCircle className="w-3 h-3" /></div>;
    case 'processing':
      return <div className="w-5 h-5 rounded-full bg-orange-500/10 flex items-center justify-center border border-orange-500/20 text-orange-500"><Loader2 className="w-3 h-3 animate-spin" /></div>;
    default:
      return <div className="w-5 h-5 rounded-full bg-zinc-800 flex items-center justify-center border border-zinc-700 text-zinc-500"><Clock className="w-3 h-3" /></div>;
  }
}
