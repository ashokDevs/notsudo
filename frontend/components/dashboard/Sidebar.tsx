"use client";

import { usePathname } from "next/navigation";
import { useSession } from "@/lib/auth-client";
import { 
  Plus,
  Search,
  ChevronUp,
  ChevronDown,
  LayoutDashboard,
  Settings,
  PanelLeft,
  Circle,
  CheckCircle2,
  Clock,
  AlertCircle
} from "lucide-react";
import { useEffect, useState, useMemo } from "react";
import { getSocket } from "@/lib/socket";
import Link from "next/link";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

interface Job {
  id: string;
  repo: string;
  issueNumber: number;
  issueTitle: string;
  status: string;
  stage: string;
  createdAt: string;
}

interface SidebarProps {
  isMobileOpen?: boolean;
  setIsMobileOpen?: (open: boolean) => void;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
}

export const OctopusIcon = ({ className }: { className?: string }) => (
  <svg 
    viewBox="0 0 24 24" 
    fill="currentColor" 
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    <path d="M12 2C9.24 2 7 4.24 7 7C7 8.38 7.56 9.63 8.47 10.53C6.44 11.23 5 13.19 5 15.5C5 17.98 7.02 20 9.5 20C10.05 20 10.58 19.9 11.07 19.72C11.34 21.04 12.51 22 13.9 22C15.61 22 17 20.61 17 18.9C17 18.66 16.97 18.43 16.92 18.21C18.15 17.51 19 16.11 19 14.5C19 12.02 16.98 10 14.5 10C14.12 10 13.76 10.05 13.41 10.14C13.79 9.24 14 8.24 14 7C14 4.24 11.76 2 9 2H12Z" />
    <circle cx="10" cy="8" r="1" fill="black" />
    <circle cx="14" cy="8" r="1" fill="black" />
  </svg>
);

export function Sidebar({ isMobileOpen, setIsMobileOpen, isCollapsed, setIsCollapsed }: SidebarProps) {
  const pathname = usePathname();
  const { data: session } = useSession();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isRecentSessionsOpen, setIsRecentSessionsOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const userId = session?.user?.id;

  const fetchJobs = async () => {
    if (!userId) return;
    try {
      const response = await fetch(`/api/jobs?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        const sorted = (Array.isArray(data) ? data : data.jobs || []).sort((a: Job, b: Job) => 
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );
        setJobs(sorted.slice(0, 10));
      }
    } catch {
      // Silently handle fetch errors - sidebar will show empty sessions
    }
  };

  useEffect(() => {
    if (userId) {
      fetchJobs();

      const socket = getSocket();
      
      socket.emit('join_user', { userId });

      socket.on('job_created', (newJob: Job) => {
        setJobs(prev => {
          // Add to top and truncate to 10
          const updated = [newJob, ...prev];
          return updated.slice(0, 10);
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

  const filteredJobs = useMemo(() => {
    if (!searchQuery) return jobs;
    return jobs.filter(job => 
      job.issueTitle?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.repo.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [jobs, searchQuery]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'processing':
        return <Circle className="w-4 h-4 text-orange-500 fill-orange-500" />;
      default:
        return <Clock className="w-4 h-4 text-zinc-500" />;
    }
  };

  if (isCollapsed) {
    return (
      <aside className="fixed left-0 top-0 h-screen w-16 bg-[#0C0C0E] border-r border-white/5 hidden md:flex flex-col items-center py-6 z-50 transition-all duration-300">
        <button 
          onClick={() => setIsCollapsed(false)}
          className="mb-8 p-2 text-zinc-400 hover:text-white transition-colors"
        >
          <PanelLeft className="w-5 h-5" />
          <div className="absolute top-2 right-2 w-2 h-2 bg-orange-500 rounded-full" />
        </button>
        
        <div className="flex flex-col gap-6 items-center flex-1">
          {navItems.map((item) => (
            <Link 
              key={item.name} 
              href={item.href}
              className={`p-2 rounded-lg transition-colors ${pathname === item.href ? 'text-orange-500' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              <item.icon className="w-5 h-5" />
            </Link>
          ))}
        </div>

        <div className="mt-auto flex flex-col gap-4 items-center mb-4">
        </div>
      </aside>
    );
  }

  return (
    <>
      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] md:hidden transition-all"
          onClick={() => setIsMobileOpen?.(false)}
        />
      )}

      <aside className={`fixed left-0 top-0 h-screen w-[280px] bg-[#0C0C0E] border-r border-white/5 flex flex-col z-[70] transition-all duration-300 font-sans selection:bg-orange-500/30 ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}>
        {/* Header */}
        <div className="p-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <OctopusIcon className="w-6 h-6 text-orange-500" />
            <span className="font-bold text-lg text-white tracking-tight">notsudo</span>
          </div>
          <div className="flex items-center gap-2">
            <Link 
              href="/dashboard/settings"
              className="p-1.5 text-zinc-500 hover:text-orange-500 transition-colors rounded-lg hover:bg-white/5"
            >
              <Settings className="w-5 h-5" />
            </Link>
            <button 
              onClick={() => {
                  if (isMobileOpen) {
                      setIsMobileOpen?.(false);
                  } else {
                      setIsCollapsed(true);
                  }
              }}
              className="text-zinc-500 hover:text-white transition-colors relative"
            >
              <PanelLeft className="w-5 h-5" />
              <div className="absolute top-0 right-0 w-1.5 h-1.5 bg-orange-500 rounded-full border border-[#0C0C0E]" />
            </button>
          </div>
        </div>

      {/* Search */}
      <div className="px-5 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input 
            type="text" 
            placeholder="Search sessions"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#15151A] border border-white/5 rounded-xl py-2 pl-10 pr-4 text-sm text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-orange-500/50 transition-all"
          />
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-5 space-y-8 scrollbar-hide pb-20">
        {/* Recent Sessions */}
        <section>
          <button 
            onClick={() => setIsRecentSessionsOpen(!isRecentSessionsOpen)}
            className="flex items-center justify-between w-full text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4 hover:text-zinc-300 transition-colors"
          >
            Recent sessions
            {isRecentSessionsOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
          
          {isRecentSessionsOpen && (
            <div className="space-y-1">
              {filteredJobs.map((job) => (
                <Link 
                  key={job.id} 
                  href={`/dashboard?job_id=${job.id}`}
                  className="group flex items-center gap-3 py-2 px-2 hover:bg-white/5 rounded-lg transition-all"
                >
                  <div className="shrink-0">
                    {job.status === 'processing' ? (
                        <div className="w-4 h-4 flex items-center justify-center">
                            <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
                        </div>
                    ) : getStatusIcon(job.status)}
                  </div>
                  <span className="text-sm text-zinc-400 group-hover:text-zinc-200 truncate transition-colors">
                    {job.issueTitle || job.issueNumber || job.id}
                  </span>
                </Link>
              ))}
              {filteredJobs.length === 0 && (
                <p className="text-xs text-zinc-600 italic px-2">No sessions found</p>
              )}
              <button className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors py-3 px-2">
                <Plus className="w-3 h-3" />
                View more
              </button>
            </div>
          )}
        </section>
      </div>

      {/* Footer - Credit Limit */}
      <div className="p-5 border-t border-white/5 bg-[#0C0C0E]/50 backdrop-blur-md">
        <div>
          <div className="flex items-center justify-between text-[11px] font-medium mb-2">
            <span className="text-zinc-500">Daily session limit (1/100)</span>
          </div>
          <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
            <div className="h-full w-[1%] bg-orange-600 rounded-full" />
          </div>
        </div>
      </div>
    </aside>
    </>
  );
}
