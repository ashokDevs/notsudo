"use client";

import { useEffect, useState } from "react";
import { Github } from "lucide-react";

// Typewriter animation component
function TypewriterText({ 
  text, 
  speed = 50, 
  delay = 2000,
  className = "" 
}: { 
  text: string; 
  speed?: number; 
  delay?: number;
  className?: string;
}) {
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    let timeout: NodeJS.Timeout;
    
    if (isTyping) {
      if (displayedText.length < text.length) {
        timeout = setTimeout(() => {
          setDisplayedText(text.slice(0, displayedText.length + 1));
        }, speed);
      } else {
        // Finished typing, wait then reset
        timeout = setTimeout(() => {
          setIsTyping(false);
          setDisplayedText("");
        }, delay);
      }
    } else {
      // Start typing again
      timeout = setTimeout(() => {
        setIsTyping(true);
      }, 500);
    }

    return () => clearTimeout(timeout);
  }, [displayedText, isTyping, text, speed, delay]);

  return (
    <span className={className}>
      {displayedText}
      <span className="inline-block w-2 h-4 bg-orange-500 ml-1 animate-pulse" />
    </span>
  );
}

// Animated cursor that moves and clicks
function AnimatedCursor() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-20">
      {/* Simple arrow cursor */}
      <div 
        className="absolute cursor-animation"
        style={{
          animation: "cursorMove 3s ease-in-out infinite",
        }}
      >
        {/* Arrow cursor SVG */}
        <svg 
          width="20" 
          height="20" 
          viewBox="0 0 24 24" 
          fill="white" 
          className="drop-shadow-lg"
          style={{
            filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.8))",
          }}
        >
          <path d="M4 4L20 12L12 14L10 22L4 4Z" />
        </svg>
      </div>
      
      <style jsx>{`
        @keyframes cursorMove {
          0%, 100% {
            top: 15%;
            left: 25%;
            opacity: 1;
          }
          35% {
            top: 40%;
            left: 42%;
            opacity: 1;
          }
          40%, 55% {
            top: 42%;
            left: 44%;
            opacity: 1;
          }
          60% {
            top: 40%;
            left: 42%;
            opacity: 1;
          }
          90% {
            top: 20%;
            left: 75%;
            opacity: 0.5;
          }
        }
      `}</style>
    </div>
  );
}

// Animated button that presses when cursor clicks
function AnimatedPublishButton() {
  return (
    <div className="relative z-10">
      <button 
        className="inline-flex items-center gap-3 bg-gray-800 text-gray-200 px-6 py-3 font-retro-body text-xl uppercase tracking-wider border border-gray-600 transition-all"
        style={{
          animation: "buttonPress 3s ease-in-out infinite",
        }}
      >
        <Github className="w-5 h-5" />
        [ Publish Branch ]
      </button>
      
      <style jsx>{`
        @keyframes buttonPress {
          0%, 35%, 60%, 100% {
            transform: translateY(0);
            box-shadow: 0 4px 0 #f97316;
          }
          40%, 55% {
            transform: translateY(4px);
            box-shadow: 0 0px 0 #f97316;
          }
        }
      `}</style>
    </div>
  );
}

interface Step {
  number: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const steps: Step[] = [
  {
    number: "01",
    title: "Select your GitHub repository and branch. Write a detailed prompt for NotSudo.",
    description: "Use the \"notsudo\" label in an issue to assign a task directly in GitHub.",
    icon: (
      <div className="w-full h-36 bg-black border border-gray-800 p-4 font-retro-body text-base text-gray-400 overflow-hidden relative retro-scanlines">
        <div className="text-orange-500 mb-2">&gt; @kathy/flipdisc main</div>
        <div className="text-gray-300">
          <TypewriterText 
            text="Can you bump the version of next.js to v15 and convert the project to use app directory?" 
            speed={40}
            delay={3000}
          />
        </div>
      </div>
    ),
  },
  {
    number: "02",
    title: "NotSudo fetches your repository, clones it to a Cloud VM, and develops a plan utilizing the latest model.",
    description: "",
    icon: (
      <div className="w-full h-36 bg-black border border-gray-800 p-4 font-retro-body text-base text-gray-400 overflow-hidden relative retro-scanlines">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-5 h-5 border border-orange-500 flex items-center justify-center text-orange-500 text-xs">N</div>
          <span className="text-orange-500">NotSudo_AI</span>
        </div>
        <div className="text-gray-300">
          <TypewriterText 
            text="Here is my plan: I plan to update the following files to the new app directory structure." 
            speed={35}
            delay={3000}
          />
        </div>
        <div className="mt-2 text-cyan-400">&gt; Update 22 Files</div>
      </div>
    ),
  },
  {
    number: "03",
    title: "NotSudo provides a diff of the changes. Quickly browse and approve code edits.",
    description: "",
    icon: (
      <div className="w-full h-36 bg-black border border-gray-800 p-4 font-retro-body text-base overflow-hidden relative leading-relaxed retro-scanlines">
        <div className="text-gray-500">&quot;dependencies&quot;: {"{"}</div>
        <div className="text-red-500 bg-red-900/20">- &quot;next&quot;: &quot;10.2.3&quot;,</div>
        <div className="text-green-500 bg-green-900/20">+ &quot;next&quot;: &quot;15.4.5&quot;,</div>
        <div className="text-gray-300">&quot;react&quot;: &quot;19.1.1&quot;,</div>
        <div className="text-gray-500">{"}"}</div>
      </div>
    ),
  },
  {
    number: "04",
    title: "NotSudo creates a PR of the changes. Approve the PR, merge it to your branch, and publish it on GitHub.",
    description: "",
    icon: (
      <div className="w-full h-36 bg-black border border-gray-800 flex items-center justify-center retro-scanlines relative overflow-hidden">
        {/* Animated cursor */}
        <AnimatedCursor />
        
        {/* Button with GitHub icon that animates */}
        <AnimatedPublishButton />
      </div>
    ),
  },
];

export function HowItWorksSection() {
  return (
    <section className="relative py-24 px-4 bg-black border-t-2 border-orange-500/30">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12">
          <span className="inline-block px-4 py-2 text-lg font-retro-body text-orange-500 border-2 border-orange-500/50 mb-6 uppercase tracking-wider">
            [ HOW IT WORKS ]
          </span>
        </div>

        {/* Steps - 2x2 Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12">
          {steps.map((step, index) => (
            <div
              key={index}
              className="flex flex-col gap-4"
            >
              {/* Step Number */}
              <div className="w-10 h-10 border-2 border-orange-500 flex items-center justify-center text-orange-500 font-retro-body text-xl">
                {step.number}
              </div>

              {/* Title */}
              <h3 className="text-lg font-retro-body text-white leading-relaxed min-h-[60px]">
                {step.title}
              </h3>

              {/* Icon/Visual */}
              <div className="mb-4">
                {step.icon}
              </div>

              {/* Description */}
              {step.description && (
                <p className="text-base font-retro-body text-gray-500 leading-relaxed">
                  {step.description}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}



