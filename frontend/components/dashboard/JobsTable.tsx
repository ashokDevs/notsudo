"use client";

import { ExternalLink } from "lucide-react";

interface Job {
  id: string;
  issueNumber: number;
  issueTitle: string | null;
  repositoryId: string | null;
  status: string;
  stage: string;
  prUrl: string | null;
  createdAt: string | null;
}

interface JobsTableProps {
  jobs: Job[];
  loading?: boolean;
}

const statusStyles: Record<string, string> = {
  processing: "bg-amber-500/20 text-amber-500 border-amber-500/30",
  completed: "bg-green-500/20 text-green-500 border-green-500/30",
  failed: "bg-red-500/20 text-red-500 border-red-500/30",
};

const stageLabels: Record<string, string> = {
  analyzing: "Analyzing",
  generating: "Generating",
  validating: "Validating",
  completed: "Completed",
  error: "Error",
};

function formatDate(dateString: string | null): string {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function JobsTable({ jobs, loading }: JobsTableProps) {
  if (loading) {
    return (
      <div className="border border-white/10 bg-black/50 p-8">
        <div className="flex items-center justify-center gap-3 text-gray-500">
          <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          <span className="font-mono text-sm">Loading jobs...</span>
        </div>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="border border-white/10 bg-black/50 p-8 text-center">
        <p className="font-mono text-gray-500 text-sm mb-2">No jobs yet</p>
        <p className="font-mono text-gray-600 text-xs">
          Jobs will appear here when you trigger them via GitHub issues
        </p>
      </div>
    );
  }

  return (
    <div className="border border-white/10 bg-black/50 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-white/10">
            <th className="text-left p-4 font-mono text-xs uppercase tracking-wider text-gray-500">
              Issue
            </th>
            <th className="text-left p-4 font-mono text-xs uppercase tracking-wider text-gray-500">
              Status
            </th>
            <th className="text-left p-4 font-mono text-xs uppercase tracking-wider text-gray-500">
              Stage
            </th>
            <th className="text-left p-4 font-mono text-xs uppercase tracking-wider text-gray-500">
              Created
            </th>
            <th className="text-left p-4 font-mono text-xs uppercase tracking-wider text-gray-500">
              PR
            </th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
              <td className="p-4">
                <div>
                  <span className="font-mono text-sm text-white">
                    #{job.issueNumber}
                  </span>
                  {job.issueTitle && (
                    <p className="font-mono text-xs text-gray-500 truncate max-w-xs">
                      {job.issueTitle}
                    </p>
                  )}
                </div>
              </td>
              <td className="p-4">
                <span className={`inline-flex px-2 py-1 text-xs font-mono uppercase border ${statusStyles[job.status] || statusStyles.processing}`}>
                  {job.status}
                </span>
              </td>
              <td className="p-4">
                <span className="font-mono text-sm text-gray-400">
                  {stageLabels[job.stage] || job.stage}
                </span>
              </td>
              <td className="p-4 font-mono text-sm text-gray-500">
                {formatDate(job.createdAt)}
              </td>
              <td className="p-4">
                {job.prUrl ? (
                  <a
                    href={job.prUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 font-mono text-xs text-amber-500 hover:text-amber-400 transition-colors"
                  >
                    View PR
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <span className="font-mono text-xs text-gray-600">-</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
