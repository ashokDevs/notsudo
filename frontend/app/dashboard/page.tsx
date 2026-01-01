"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { JobsTable } from "@/components/dashboard/JobsTable";
import { RepositoriesGrid } from "@/components/dashboard/RepositoriesGrid";
import { useSession } from "@/lib/auth-client";
import { 
  Briefcase, 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  GitBranch,
  RefreshCw
} from "lucide-react";

interface Stats {
  total_jobs: number;
  processing_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  total_repos: number;
}

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

interface Repository {
  id: string;
  name: string;
  fullName: string;
  description: string | null;
  isPrivate: boolean;
  htmlUrl: string;
  language: string | null;
  defaultBranch: string | null;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Dashboard() {
  const router = useRouter();
  const { data: session, isPending } = useSession();
  
  const [stats, setStats] = useState<Stats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    if (!session?.user?.id) return;
    
    try {
      // Fetch all data in parallel
      const [statsRes, jobsRes, reposRes] = await Promise.all([
        fetch(`${API_URL}/api/stats?user_id=${session.user.id}`),
        fetch(`${API_URL}/api/jobs?user_id=${session.user.id}`),
        fetch(`${API_URL}/api/repos?user_id=${session.user.id}`),
      ]);

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      if (jobsRes.ok) {
        const jobsData = await jobsRes.json();
        setJobs(Array.isArray(jobsData) ? jobsData : jobsData.jobs || []);
      }

      if (reposRes.ok) {
        const reposData = await reposRes.json();
        setRepositories(Array.isArray(reposData) ? reposData : reposData.repos || []);
      }

      setLastUpdated(new Date());
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
    }
  }, [session?.user?.id]);

  // Initial fetch
  useEffect(() => {
    if (session?.user?.id) {
      fetchData();
    }
  }, [session?.user?.id, fetchData]);

  // Polling every 30 seconds
  useEffect(() => {
    if (!session?.user?.id) return;

    const interval = setInterval(() => {
      fetchData();
    }, 30000);

    return () => clearInterval(interval);
  }, [session?.user?.id, fetchData]);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  // Show loading while checking auth
  if (isPending) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-500">
          <div className="w-6 h-6 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          <span className="font-mono text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!session) {
    return null;
  }

  const handleConnectRepo = () => {
    router.push("/dashboard/settings");
  };

  return (
    <div className="min-h-screen bg-black">
      <Sidebar />
      
      {/* Main Content */}
      <main className="ml-64 min-h-screen">
        {/* Header */}
        <header className="h-16 border-b border-white/10 flex items-center justify-between px-8">
          <h1 className="font-mono text-xl font-bold text-white">Overview</h1>
          <div className="flex items-center gap-4">
            {lastUpdated && (
              <span className="font-mono text-xs text-gray-500">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button 
              onClick={fetchData}
              className="p-2 hover:bg-white/5 rounded transition-colors text-gray-500 hover:text-white"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </header>

        <div className="p-8 space-y-8">
          {/* Stats Grid */}
          <section>
            <h2 className="font-mono text-xs uppercase tracking-wider text-gray-500 mb-4">
              Statistics
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatsCard
                title="Total Jobs"
                value={stats?.total_jobs ?? 0}
                icon={<Briefcase className="w-5 h-5" />}
              />
              <StatsCard
                title="Processing"
                value={stats?.processing_jobs ?? 0}
                icon={<Loader2 className="w-5 h-5" />}
                variant="processing"
              />
              <StatsCard
                title="Completed"
                value={stats?.completed_jobs ?? 0}
                icon={<CheckCircle2 className="w-5 h-5" />}
                variant="completed"
              />
              <StatsCard
                title="Failed"
                value={stats?.failed_jobs ?? 0}
                icon={<XCircle className="w-5 h-5" />}
                variant="failed"
              />
            </div>
          </section>

          {/* Active Jobs */}
          <section>
            <h2 className="font-mono text-xs uppercase tracking-wider text-gray-500 mb-4">
              Recent Jobs
            </h2>
            <JobsTable jobs={jobs} loading={loading} />
          </section>

          {/* Repositories */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-mono text-xs uppercase tracking-wider text-gray-500">
                Repositories ({repositories.length})
              </h2>
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-gray-500" />
              </div>
            </div>
            <RepositoriesGrid 
              repositories={repositories} 
              loading={loading}
              onConnect={handleConnectRepo}
            />
          </section>
        </div>
      </main>
    </div>
  );
}
