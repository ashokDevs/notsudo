"use client";

import React, { useState, useEffect } from "react";
import { Terminal, Clock, CheckCircle2, AlertCircle, Loader2, Github, MoreHorizontal, Play } from "lucide-react";
import Link from "next/link";
import { useSession } from "@/lib/auth-client";
import { getSocket } from "@/lib/socket";

interface Job {
  id: string;
  repo: string;
  issueTitle: string;
  status: "processing" | "completed" | "failed" | "generating" | "analyzing" | "paused";
  createdAt: string;
  prUrl?: string;
  error?: string;
}

export default function RecentSessions() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const { data: session } = useSession();
  const userId = session?.user?.id;

  const fetchJobs = async () => {
    if (!userId) return;
    try {
      const res = await fetch(`/api/jobs?user_id=${userId}`);
      const data = await res.json();
      setJobs(Array.isArray(data) ? data.slice(0, 5) : (data.jobs ? data.jobs.slice(0, 5) : []));
    } catch (err) {
      console.error("Failed to fetch jobs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchJobs();

      const socket = getSocket();
      
      socket.emit('join_user', { userId });

      socket.on('job_created', (newJob: Job) => {
        setJobs(prev => {
          // Add to top and truncate to 5
          const updated = [newJob, ...prev];
          return updated.slice(0, 5);
        });
      });

      socket.on('job_updated', (updatedJob: Job) => {
        setJobs(prev => prev.map(j => j.id === updatedJob.id ? { ...j, ...updatedJob } : j));
      });

      return () => {
        socket.emit('leave_user', { userId });
        socket.off('job_created');
        socket.off('job_updated');
      };
    }
  }, [userId]);

  const getStatusBadge = (status: Job["status"]) => {
    switch (status) {
      case "completed":
        return <span className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 text-emerald-500 text-[10px] font-bold rounded-md border border-emerald-500/20"><CheckCircle2 className="w-3 h-3" /> COMPLETED</span>;
      case "failed":
        return <span className="flex items-center gap-1.5 px-2 py-0.5 bg-red-500/10 text-red-500 text-[10px] font-bold rounded-md border border-red-500/20"><AlertCircle className="w-3 h-3" /> FAILED</span>;
      case "paused":
        return <span className="flex items-center gap-1.5 px-2 py-0.5 bg-zinc-800 text-zinc-400 text-[10px] font-bold rounded-md border border-zinc-700">PAUSED</span>;
      default:
        return <span className="flex items-center gap-1.5 px-2 py-0.5 bg-orange-500/10 text-orange-400 text-[10px] font-bold rounded-md border border-orange-500/20"><Loader2 className="w-3 h-3 animate-spin" /> EXECUTING</span>;
    }
  };

  if (loading && jobs.length === 0) {
    return (
      <div className="py-20 flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-6 h-6 text-orange-500 animate-spin" />
        <span className="text-zinc-500 text-sm font-medium">Syncing sessions...</span>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-zinc-500" />
          <h2 className="text-sm font-semibold text-zinc-100 uppercase tracking-tight">Sessions</h2>
        </div>
        <Link 
          href="/jobs" 
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          View all
        </Link>
      </div>

      <div className="flex flex-col gap-3">
        {jobs.length > 0 ? (
          jobs.map((job) => (
            <div
              key={job.id}
              className="group flex items-center justify-between p-4 bg-zinc-900/20 border border-zinc-800/40 rounded-xl hover:border-orange-500/30 hover:bg-zinc-800/20 transition-all cursor-pointer"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0">
                  <Github className="w-5 h-5 text-zinc-600 group-hover:text-orange-500/60 transition-colors" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-zinc-100 truncate mb-1">
                    {job.issueTitle || job.id}
                  </h3>
                  <div className="flex items-center gap-3">
                    {getStatusBadge(job.status)}
                    <span className="text-[10px] text-zinc-600 flex items-center gap-1 uppercase font-semibold">
                      <Clock className="w-3 h-3" /> {new Date(job.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Link
                  href={`/jobs/${job.id}`}
                  className="p-2 text-zinc-500 hover:text-zinc-200"
                >
                  <Play className="w-4 h-4 fill-current" />
                </Link>
                <button className="p-2 text-zinc-500 hover:text-zinc-200">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="bg-zinc-900/10 border-2 border-dashed border-zinc-800/50 p-12 rounded-2xl text-center">
             <span className="text-sm text-zinc-600 font-medium">No sessions recorded yet</span>
          </div>
        )}
      </div>
      
      {jobs.length > 0 && (
         <button className="w-full mt-6 py-3 text-xs font-semibold text-zinc-500 hover:text-zinc-300 transition-colors">
           VIEW MORE
         </button>
      )}
    </div>
  );
}
