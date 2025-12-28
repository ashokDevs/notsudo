"use client";

import { Sidebar } from "@/components/dashboard/Sidebar";
import { Github, Check, AlertCircle } from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
  const [isConnected, setIsConnected] = useState(false);

  const handleConnectGithub = () => {
    // TODO: Implement GitHub OAuth flow
    // For now, just simulate connection
    setIsConnected(true);
  };

  return (
    <div className="min-h-screen bg-black">
      <Sidebar />
      
      {/* Main Content */}
      <main className="ml-64 min-h-screen">
        {/* Header */}
        <header className="h-16 border-b border-white/10 flex items-center px-8">
          <h1 className="font-mono text-xl font-bold text-white">Settings</h1>
        </header>

        <div className="p-8">
          <div className="max-w-2xl">
            {/* GitHub Connection */}
            <div className="border border-white/10 rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-white/10">
                <h2 className="font-mono text-white font-medium">GitHub Connection</h2>
                <p className="font-mono text-xs text-gray-500 mt-1">
                  Connect your GitHub account to enable automated code reviews
                </p>
              </div>
              <div className="p-6">
                {isConnected ? (
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-green-500/20 border border-green-500/30 flex items-center justify-center">
                      <Check className="w-6 h-6 text-green-500" />
                    </div>
                    <div>
                      <p className="font-mono text-sm text-white">Connected to GitHub</p>
                      <p className="font-mono text-xs text-gray-500">Your account is linked</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-start gap-3 p-4 bg-orange-500/5 border border-orange-500/20 rounded-lg">
                      <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                      <p className="font-mono text-sm text-gray-400">
                        Connect your GitHub account to allow NotSudo to analyze your repositories and create pull requests.
                      </p>
                    </div>
                    <button
                      onClick={handleConnectGithub}
                      className="inline-flex items-center gap-3 px-6 py-3 bg-white text-black font-mono text-sm font-medium hover:bg-gray-100 transition-colors rounded-lg"
                    >
                      <Github className="w-5 h-5" />
                      Connect to GitHub
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
