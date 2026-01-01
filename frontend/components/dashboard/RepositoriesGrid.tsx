"use client";

import { GitBranch, Lock, Unlock, ExternalLink, Plus } from "lucide-react";

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

interface RepositoriesGridProps {
  repositories: Repository[];
  loading?: boolean;
  onConnect?: () => void;
}

const languageColors: Record<string, string> = {
  TypeScript: "bg-blue-500",
  JavaScript: "bg-yellow-500",
  Python: "bg-green-500",
  Go: "bg-cyan-500",
  Rust: "bg-orange-500",
  Java: "bg-red-500",
  Ruby: "bg-red-400",
  PHP: "bg-purple-500",
  C: "bg-gray-500",
  "C++": "bg-pink-500",
  "C#": "bg-purple-400",
};

export function RepositoriesGrid({ repositories, loading, onConnect }: RepositoriesGridProps) {
  if (loading) {
    return (
      <div className="border border-white/10 bg-black/50 p-8">
        <div className="flex items-center justify-center gap-3 text-gray-500">
          <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          <span className="font-mono text-sm">Loading repositories...</span>
        </div>
      </div>
    );
  }

  if (repositories.length === 0) {
    return (
      <div className="border border-white/10 border-dashed bg-black/30 p-8 text-center">
        <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-4">
          <Plus className="w-6 h-6 text-amber-500" />
        </div>
        <p className="font-mono text-white text-sm mb-2">No repositories connected</p>
        <p className="font-mono text-gray-600 text-xs mb-4">
          Connect a repository to start processing issues
        </p>
        {onConnect && (
          <button
            onClick={onConnect}
            className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 text-black font-mono text-sm font-bold hover:bg-amber-400 transition-colors"
          >
            Connect Repository
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {repositories.map((repo) => (
        <div
          key={repo.id}
          className="relative border border-white/10 bg-black/50 p-5 hover:border-white/20 transition-colors group"
        >
          {/* Grid background */}
          <div 
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage: `
                linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)
              `,
              backgroundSize: '16px 16px',
            }}
          />
          
          {/* Corner markers */}
          <span className="absolute top-1.5 left-1.5 text-white/10 font-mono text-[10px]">+</span>
          <span className="absolute top-1.5 right-1.5 text-white/10 font-mono text-[10px]">+</span>
          
          <div className="relative z-10">
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-gray-500" />
                <span className="font-mono text-sm text-white font-medium truncate max-w-[180px]">
                  {repo.name}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {repo.isPrivate ? (
                  <Lock className="w-3.5 h-3.5 text-gray-500" />
                ) : (
                  <Unlock className="w-3.5 h-3.5 text-gray-500" />
                )}
              </div>
            </div>
            
            {/* Full name */}
            <p className="font-mono text-xs text-gray-500 mb-2 truncate">
              {repo.fullName}
            </p>
            
            {/* Description */}
            {repo.description && (
              <p className="font-mono text-xs text-gray-400 mb-3 line-clamp-2">
                {repo.description}
              </p>
            )}
            
            {/* Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-white/5">
              {/* Language */}
              <div className="flex items-center gap-1.5">
                {repo.language && (
                  <>
                    <span className={`w-2 h-2 rounded-full ${languageColors[repo.language] || "bg-gray-500"}`} />
                    <span className="font-mono text-xs text-gray-500">{repo.language}</span>
                  </>
                )}
              </div>
              
              {/* Link */}
              <a
                href={repo.htmlUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-mono text-xs text-gray-500 hover:text-amber-500 transition-colors opacity-0 group-hover:opacity-100"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
