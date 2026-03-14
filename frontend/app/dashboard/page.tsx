"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { OnboardingModal } from "@/components/dashboard/OnboardingModal";
import { useSession } from "@/lib/auth-client";
import RepoSelector from "@/components/dashboard/RepoSelector";
import { ModelSelector } from "@/components/dashboard/ModelSelector";
import PromptInput from "@/components/dashboard/PromptInput";
import RecentSessions from "@/components/dashboard/RecentSessions";
import { Loader2 } from "lucide-react";

interface GitHubLabel {
  name: string;
  color?: string;
}

interface GitHubIssue {
  number: number;
  title: string;
  created_at: string;
  labels: GitHubLabel[];
}

export default function Dashboard() {
  const router = useRouter();
  const { data: session, isPending } = useSession();
  
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("gemini-1.5-pro");
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState("OVERVIEW");
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [autoFindIssues] = useState(true);
  const [suggestedIssues, setSuggestedIssues] = useState<GitHubIssue[]>([]);
  const [loadingIssues, setLoadingIssues] = useState(false);

  useEffect(() => {
    const savedRepo = localStorage.getItem("notsudo_selected_repo");
    if (savedRepo) setSelectedRepo(savedRepo);
  }, []);

  useEffect(() => {
    if (selectedRepo) {
      localStorage.setItem("notsudo_selected_repo", selectedRepo);
    }
  }, [selectedRepo]);

  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  useEffect(() => {
    const hasSeenOnboarding = localStorage.getItem("notsudo_onboarding_seen");
    if (!hasSeenOnboarding) {
      setShowOnboarding(true);
    }
  }, []);

  useEffect(() => {
    async function fetchIssues(): Promise<void> {
      if (!selectedRepo || !autoFindIssues) return;

      setLoadingIssues(true);
      try {
        const res = await fetch(`/api/repos/${selectedRepo}/issues`);
        const data = await res.json();
        if (data.issues) {
          setSuggestedIssues(data.issues);
          if (data.issues.length > 0 && activeTab === "OVERVIEW") {
            setActiveTab("SUGGESTED");
          }
        }
      } finally {
        setLoadingIssues(false);
      }
    }

    fetchIssues();
  }, [selectedRepo, autoFindIssues, activeTab]);

  function handleCloseOnboarding(): void {
    setShowOnboarding(false);
    localStorage.setItem("notsudo_onboarding_seen", "true");
  }

  async function handlePromptSubmit(prompt: string): Promise<void> {
    if (!selectedRepo || !session?.user?.id) return;

    setIsProcessing(true);
    try {
      await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo: selectedRepo,
          prompt: prompt,
          user_id: session.user.id
        })
      });
    } finally {
      setIsProcessing(false);
    }
  }

  if (isPending) {
    return (
      <div className="min-h-screen bg-[#020202] flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-500 font-medium">Booting system...</span>
        </div>
      </div>
    );
  }

  if (!session) return null;

  return (
    <div className="min-h-screen bg-[#020202] text-zinc-100 font-modern selection:bg-orange-500/30">
      <OnboardingModal isOpen={showOnboarding} onClose={handleCloseOnboarding} />

      {/* Main Dashboard Content */}
      <main className="max-w-4xl mx-auto py-16 px-6">
        {/* Selectors and Input Area */}
        <div className="mb-10 space-y-4">
          <div className="flex items-center gap-3">
            <RepoSelector onSelect={setSelectedRepo} selectedRepo={selectedRepo} />
            <ModelSelector onSelect={setSelectedModel} selectedModelId={selectedModel} />
          </div>
          
          <PromptInput 
            onSubmit={handlePromptSubmit} 
            isLoading={isProcessing} 
            repoSelected={!!selectedRepo} 
          />
        </div>

        {/* Structured Tabs and Controls */}
        <div className="modern-card overflow-hidden">
          <div className="flex border-b border-zinc-800/60 transition-all">
            {["Codebase overview", "Suggested", "Scheduled"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab.toUpperCase())}
                className={`py-4 px-6 text-sm font-medium transition-all relative ${
                  activeTab === tab.toUpperCase() 
                    ? "text-white" 
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {tab}
                {activeTab === tab.toUpperCase() && (
                  <div className="absolute bottom-[-1px] left-4 right-4 h-0.5 bg-orange-600 rounded-full" />
                )}
              </button>
            ))}
          </div>

          <div className="p-6">

            {activeTab === "OVERVIEW" && <RecentSessions />}
            
            {activeTab === "SUGGESTED" && (
              <div className="space-y-4">
                {loadingIssues ? (
                  <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                    <p className="text-sm text-zinc-500 font-medium">Scanning for low-hanging fruit...</p>
                  </div>
                ) : suggestedIssues.length === 0 ? (
                  <div className="text-center py-20 border-2 border-dashed border-zinc-800 rounded-2xl">
                    <p className="text-zinc-500 font-medium">No open issues found in this repository.</p>
                  </div>
                ) : (
                  suggestedIssues.map((issue) => (
                    <div 
                      key={issue.number}
                      className="group p-5 bg-zinc-900/50 border border-zinc-800 rounded-2xl hover:border-orange-500/30 transition-all cursor-pointer"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="text-[10px] font-bold text-orange-500 uppercase tracking-widest bg-orange-500/10 px-2 py-0.5 rounded border border-orange-500/20">
                              Issue #{issue.number}
                            </span>
                            <span className="text-[10px] text-zinc-600 font-medium tracking-tight">
                              Opened {new Date(issue.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <h4 className="text-sm font-bold text-zinc-100 group-hover:text-orange-400 transition-colors truncate">
                            {issue.title}
                          </h4>
                          {issue.labels && issue.labels.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-3">
                              {issue.labels.map((label: GitHubLabel) => (
                                <span
                                  key={label.name}
                                  className="text-[9px] px-2 py-0.5 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-400 font-medium"
                                  style={{ borderColor: label.color ? `#${label.color}40` : undefined }}
                                >
                                  {label.name}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <button
                          className="flex items-center gap-2 px-4 py-2 bg-white text-black text-xs font-bold rounded-xl opacity-0 group-hover:opacity-100 transition-all hover:bg-zinc-200 active:scale-95"
                          onClick={() => {
                             const input = document.querySelector('textarea') as HTMLTextAreaElement | null;
                             if (input) {
                               input.value = `Fix issue #${issue.number}: ${issue.title}`;
                               input.focus();
                             }
                          }}
                        >
                          Address issue
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "SCHEDULED" && (
              <div className="text-center py-20 border-2 border-dashed border-zinc-800 rounded-2xl">
                <p className="text-zinc-500 font-medium">Automated maintenance runs will appear here.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
