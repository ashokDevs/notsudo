"use client";

import { useEffect, useState } from "react";
import {
  ExternalLink,
  Github,
  AlertCircle,
  CheckCircle2,
  Clock,
  ChevronDown,
  ChevronUp,
  FileText
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Job {
  id: string;
  repo: string;
  issueNumber: number;
  issueTitle: string;
  status: string;
  stage: string;
  createdAt: string;
  completedAt?: string;
  prUrl?: string;
  error?: string;
  logs: string[];
  validationLogs: string[];
}

export function JobsTable() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      const response = await fetch("/api/jobs");
      if (response.ok) {
        const data = await response.json();
        setJobs(data);
      }
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const calculateDuration = (start: string, end?: string) => {
    if (!end) return "Running...";
    const startTime = new Date(start).getTime();
    const endTime = new Date(end).getTime();
    const durationMs = endTime - startTime;

    const seconds = Math.floor((durationMs / 1000) % 60);
    const minutes = Math.floor((durationMs / (1000 * 60)) % 60);
    const hours = Math.floor((durationMs / (1000 * 60 * 60)));

    if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
    if (minutes > 0) return `${minutes}m ${seconds}s`;
    return `${seconds}s`;
  };

  const toggleExpand = (jobId: string) => {
    setExpandedJobId(expandedJobId === jobId ? null : jobId);
  };

  if (loading && jobs.length === 0) {
    return (
      <div className="flex justify-center items-center p-8 text-gray-400">
        Loading jobs...
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <Card className="bg-black/40 border-white/10">
        <CardContent className="p-8 text-center text-gray-400">
          No jobs found. Start by creating a new task.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-black/40 border-white/10">
      <CardHeader>
        <CardTitle className="text-white">Job History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10 text-gray-400 text-sm">
                <th className="pb-3 pl-4 font-medium">Repository</th>
                <th className="pb-3 font-medium">Issue</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Duration</th>
                <th className="pb-3 font-medium">Date</th>
                <th className="pb-3 pr-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {jobs.map((job) => (
                <>
                  <tr
                    key={job.id}
                    className={`border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer ${expandedJobId === job.id ? 'bg-white/5' : ''}`}
                    onClick={() => toggleExpand(job.id)}
                  >
                    <td className="py-4 pl-4 text-white font-mono">
                      {job.repo}
                    </td>
                    <td className="py-4">
                      <a
                        href={`https://github.com/${job.repo}/issues/${job.issueNumber}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1 w-fit"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Github className="w-3 h-3" />
                        #{job.issueNumber}
                      </a>
                    </td>
                    <td className="py-4">
                      <div className="flex items-center gap-2">
                        {job.status === 'completed' ? (
                          <Badge className="bg-green-500/20 text-green-400 border-green-500/50 hover:bg-green-500/30">
                            Completed
                          </Badge>
                        ) : job.status === 'failed' ? (
                          <Badge className="bg-red-500/20 text-red-400 border-red-500/50 hover:bg-red-500/30">
                            Failed
                          </Badge>
                        ) : (
                          <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/50 hover:bg-blue-500/30">
                            {job.status}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-4 text-gray-300 font-mono text-xs">
                      {calculateDuration(job.createdAt, job.completedAt)}
                    </td>
                    <td className="py-4 text-gray-400 text-xs">
                      {new Date(job.createdAt).toLocaleString()}
                    </td>
                    <td className="py-4 pr-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {job.prUrl && (
                          <a
                            href={job.prUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 hover:bg-white/10 rounded-md text-gray-400 hover:text-white transition-colors"
                            title="View PR"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                        >
                          {expandedJobId === job.id ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </td>
                  </tr>
                  {expandedJobId === job.id && (
                    <tr className="bg-black/20">
                      <td colSpan={6} className="p-4">
                        <div className="grid gap-4">
                          {job.error && (
                            <div className="p-4 rounded-md bg-red-950/30 border border-red-500/20 text-red-300 text-sm font-mono">
                              <div className="flex items-center gap-2 mb-2 font-bold">
                                <AlertCircle className="w-4 h-4" />
                                Error Details
                              </div>
                              {job.error}
                            </div>
                          )}

                          <div className="rounded-md border border-white/10 bg-black/50 overflow-hidden">
                            <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-white/5">
                              <span className="text-xs font-medium text-gray-400 flex items-center gap-2">
                                <FileText className="w-3 h-3" />
                                Execution Logs
                              </span>
                            </div>
                            <div className="p-4 max-h-60 overflow-y-auto font-mono text-xs text-gray-300 space-y-1">
                              {job.logs.map((log, i) => (
                                <div key={i} className="border-b border-white/5 last:border-0 pb-1 last:pb-0">
                                  {log}
                                </div>
                              ))}
                              {job.validationLogs && job.validationLogs.length > 0 && (
                                <>
                                  <div className="mt-4 mb-2 text-blue-400 font-bold border-t border-white/10 pt-2">Validation Logs:</div>
                                  {job.validationLogs.map((log, i) => (
                                    <div key={`val-${i}`} className="text-gray-400">
                                      {log}
                                    </div>
                                  ))}
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
