"use client";

import { useState } from "react";
import { X, ChevronRight, Check, Play, Github } from "lucide-react";

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function OnboardingModal({ isOpen, onClose }: OnboardingModalProps) {
  const [step, setStep] = useState(0);

  if (!isOpen) return null;

  const steps = [
    {
      title: "Welcome to NotSudo",
      description: "Your AI-powered junior developer that never sleeps. We're here to help you automate your coding tasks.",
      icon: <span className="text-2xl">👋</span>,
    },
    {
      title: "Trigger with @notsudo",
      description: "Simply mention @notsudo in any GitHub issue to trigger the automation. We'll analyze the issue and open a PR for you.",
      icon: <span className="text-2xl">🤖</span>,
    },
    {
      title: "Ready to Start?",
      description: "Check out our sample repository or watch a quick video to see how it works.",
      icon: <span className="text-2xl">🚀</span>,
      content: (
        <div className="flex flex-col gap-3 mt-4">
          <a
            href="https://github.com/notsudo-test/sample-repo"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors border border-gray-700"
          >
            <Github className="w-5 h-5 text-white" />
            <div className="text-left">
              <div className="font-medium text-white">Sample Repository</div>
              <div className="text-xs text-gray-400">Try it out here</div>
            </div>
          </a>
          <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg border border-gray-700 opacity-50 cursor-not-allowed">
            <Play className="w-5 h-5 text-white" />
            <div className="text-left">
              <div className="font-medium text-white">Watch Tutorial</div>
              <div className="text-xs text-gray-400">Coming soon</div>
            </div>
          </div>
        </div>
      ),
    },
  ];

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        {/* Progress Bar */}
        <div className="h-1 bg-gray-800 w-full">
          <div
            className="h-full bg-orange-500 transition-all duration-300 ease-out"
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          />
        </div>

        <div className="p-8">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
             <div className="w-12 h-12 bg-orange-500/10 rounded-full flex items-center justify-center border border-orange-500/20">
                {steps[step].icon}
             </div>
             <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
               <X className="w-5 h-5" />
             </button>
          </div>

          {/* Content */}
          <h2 className="text-2xl font-bold text-white mb-2 font-mono">
            {steps[step].title}
          </h2>
          <p className="text-gray-400 mb-6 leading-relaxed font-mono text-sm">
            {steps[step].description}
          </p>

          {steps[step].content}

          {/* Footer */}
          <div className="mt-8 flex justify-end">
            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-6 py-2.5 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-lg transition-colors font-mono text-sm"
            >
              {step === steps.length - 1 ? (
                <>
                  Get Started <Check className="w-4 h-4" />
                </>
              ) : (
                <>
                  Next <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
