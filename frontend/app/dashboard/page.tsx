"use client";

import { Sidebar } from "@/components/dashboard/Sidebar";
import { OnboardingModal } from "@/components/dashboard/OnboardingModal";
import { AlertTriangle } from "lucide-react";
import { useState, useEffect } from "react";

export default function Dashboard() {
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    // Check if onboarding has been seen
    const hasSeenOnboarding = localStorage.getItem("notsudo_onboarding_seen");
    if (!hasSeenOnboarding) {
      setShowOnboarding(true);
    }
  }, []);

  const handleCloseOnboarding = () => {
    setShowOnboarding(false);
    localStorage.setItem("notsudo_onboarding_seen", "true");
  };

  return (
    <div className="min-h-screen bg-black">
      <Sidebar />
      <OnboardingModal isOpen={showOnboarding} onClose={handleCloseOnboarding} />
      
      {/* Main Content */}
      <main className="ml-64 min-h-screen">
        {/* Header */}
        <header className="h-16 border-b border-white/10 flex items-center px-8">
          <h1 className="font-mono text-xl font-bold text-white">Jobs</h1>
        </header>

        <div className="p-8">
          {/* Maintenance Warning */}
          <div className="max-w-2xl mx-auto mt-20">
            <div className="border border-orange-500/30 bg-orange-500/5 rounded-lg p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-orange-500/20 border border-orange-500/30 flex items-center justify-center mx-auto mb-6">
                <AlertTriangle className="w-8 h-8 text-orange-500" />
              </div>
              <h2 className="font-mono text-2xl text-white font-bold mb-3">
                Under Maintenance
              </h2>
              <p className="font-mono text-gray-400 text-sm max-w-md mx-auto">
                We&apos;re currently working on improving the dashboard experience. 
                Please check back soon for updates.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
