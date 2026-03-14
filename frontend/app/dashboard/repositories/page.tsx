"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { RepositoriesGrid } from "@/components/dashboard/RepositoriesGrid";
import { useSession } from "@/lib/auth-client";
import { getSocket } from "@/lib/socket";

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

  const fetchRepositories = useCallback(async () => {
    if (!session?.user?.id) return;

    try {
      const response = await fetch(`${API_URL}/api/repos?user_id=${session.user.id}`);
      if (response.ok) {
        const data = await response.json();
        setRepositories(Array.isArray(data) ? data : data.repos || []);
      }
    } finally {
      setLoading(false);
    }
  }, [session?.user?.id]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchRepositories();
    }
  }, [session?.user?.id, fetchRepositories]);

  useEffect(() => {
    if (!session?.user?.id) return;
    
    const socket = getSocket();
    const userId = session.user.id;
    
    socket.emit('join_user', { userId });
    
    socket.on('repos_updated', () => {
      fetchRepositories();
    });
    
    return () => {
      socket.emit('leave_user', { userId });
      socket.off('repos_updated');
    };
  }, [session?.user?.id, fetchRepositories]);

  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  if (isPending) {
    return (
      <div className="min-h-screen bg-[#020202] flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!session) return null;

  function handleConnectRepo(): void {
    router.push("/dashboard/settings");
  }

  return (
    <div className="min-h-screen bg-[#020202] text-zinc-100 font-modern selection:bg-orange-500/30">
      {/* Main Content */}
      <main className="max-w-6xl mx-auto py-16 px-6">
        <RepositoriesGrid 
          repositories={repositories} 
          loading={loading}
          onConnect={handleConnectRepo}
        />
      </main>
    </div>
  );
}
