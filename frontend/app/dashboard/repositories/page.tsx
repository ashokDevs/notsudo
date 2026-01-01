"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { RepositoriesGrid } from "@/components/dashboard/RepositoriesGrid";
import { useSession } from "@/lib/auth-client";
import { RefreshCw } from "lucide-react";

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

export default function RepositoriesPage() {
  const router = useRouter();
  const { data: session, isPending } = useSession();
  
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchRepositories = useCallback(async () => {
    if (!session?.user?.id) return;
    
    try {
      const response = await fetch(`${API_URL}/api/repos?user_id=${session.user.id}`);
      if (response.ok) {
        const data = await response.json();
        setRepositories(Array.isArray(data) ? data : data.repos || []);
      }
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Failed to fetch repositories:", error);
    } finally {
      setLoading(false);
    }
  }, [session?.user?.id]);

  // Initial fetch
  useEffect(() => {
    if (session?.user?.id) {
      fetchRepositories();
    }
  }, [session?.user?.id, fetchRepositories]);

  // Polling every 30 seconds
  useEffect(() => {
    if (!session?.user?.id) return;

    const interval = setInterval(() => {
      fetchRepositories();
    }, 30000);

    return () => clearInterval(interval);
  }, [session?.user?.id, fetchRepositories]);

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
          <h1 className="font-mono text-xl font-bold text-white">Repositories</h1>
          <div className="flex items-center gap-4">
            {lastUpdated && (
              <span className="font-mono text-xs text-gray-500">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button 
              onClick={fetchRepositories}
              className="p-2 hover:bg-white/5 rounded transition-colors text-gray-500 hover:text-white"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </header>

        <div className="p-8">
          {/* Repositories Grid */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-mono text-xs uppercase tracking-wider text-gray-500">
                Connected Repositories ({repositories.length})
              </h2>
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
