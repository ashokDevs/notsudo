"use client";

import { Sidebar } from "@/components/dashboard/Sidebar";
import { Github, Check, AlertCircle, LogOut } from "lucide-react";
import { authClient } from "@/lib/auth-client";

export default function SettingsPage() {
  const { data: session } = authClient.useSession();
  const isConnected = !!session;

  const handleConnectGithub = async () => {
    await authClient.signIn.social({
        provider: "github",
        callbackURL: "/dashboard/settings"
    });
  };

  const handleDisconnect = async () => {
    await authClient.signOut();
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
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center gap-4">
                      {session?.user?.image ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={session.user.image}
                          alt={session.user.name || "User"}
                          className="w-12 h-12 rounded-full border border-white/10"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-full bg-green-500/20 border border-green-500/30 flex items-center justify-center">
                          <Check className="w-6 h-6 text-green-500" />
                        </div>
                      )}
                      <div>
                        <p className="font-mono text-sm text-white">
                          Connected as {session?.user?.name || "User"}
                        </p>
                        <p className="font-mono text-xs text-gray-500">
                           {session?.user?.email}
                        </p>
                      </div>
                    </div>

                    <div className="mt-2 p-3 bg-white/5 rounded border border-white/10">
                        <p className="font-mono text-xs text-gray-400 mb-2">Granted Scopes:</p>
                        <div className="flex flex-wrap gap-2">
                            <span className="px-2 py-1 bg-green-500/10 text-green-400 text-xs font-mono rounded border border-green-500/20">repo</span>
                            <span className="px-2 py-1 bg-green-500/10 text-green-400 text-xs font-mono rounded border border-green-500/20">user</span>
                            <span className="px-2 py-1 bg-green-500/10 text-green-400 text-xs font-mono rounded border border-green-500/20">read:org</span>
                        </div>
                    </div>

                    <button
                        onClick={handleDisconnect}
                        className="inline-flex items-center gap-2 px-4 py-2 mt-2 bg-red-500/10 text-red-400 font-mono text-xs font-medium hover:bg-red-500/20 transition-colors rounded border border-red-500/20 w-fit"
                    >
                        <LogOut className="w-4 h-4" />
                        Disconnect
                    </button>
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
