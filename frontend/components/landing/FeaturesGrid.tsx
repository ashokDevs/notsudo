"use client";

import { ArrowRight, Bot, Code2, GitPullRequest, Shield, Zap, Layers, Coffee } from "lucide-react";

// Floating capability pills - these will animate across the right side
const capabilityPills = [
  ["Fix bugs in minutes", "Resolve GitHub issues"],
  ["Generate pull requests", "Write unit tests"],
  ["Refactor messy code", "Update dependencies"],
  ["Close stale issues", "Apply security patches"],
  ["Fix CI failures", "Add missing types"],
  ["Resolve merge conflicts", "Update configs"],
];

const featureCards = [
  {
    icon: Zap,
    title: "Sub-5 minute resolution",
    description: "From issue to PR in under 5 minutes on average, keeping your development velocity high.",
  },
  {
    icon: Shield,
    title: "Sandbox validation",
    description: "All changes validated in isolated Docker containers before creating PRs.",
  },
  {
    icon: Layers,
    title: "100+ languages supported",
    description: "Works with Python, Node.js, Go, Rust, Java, and all major programming languages.",
  },
  {
    icon: Coffee,
    title: "No PTO, No Promotions",
    description: "Doesn't take leaves, ask for raises, or need coffee breaks. Just ships code 24/7.",
  },
];

export function FeaturesGrid() {
  return (
    <section className="relative py-24 px-4 bg-black overflow-hidden">
      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Section Label */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-sm font-medium text-gray-400 uppercase tracking-wider">
            CAPABILITIES
          </span>
        </div>

        {/* Main Content Card */}
        <div className="relative rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.03] to-transparent overflow-hidden min-h-[450px] mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 h-full min-h-[450px]">
            {/* Left Side - Text Content */}
            <div className="relative z-10 p-8 lg:p-12 flex flex-col justify-center">
              <h2 className="text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
                Fix issues,
                <br />
                ship PRs faster
              </h2>
              <p className="text-lg text-gray-400 mb-8">
                Tag @notsudo on any GitHub issue and get a working PR in minutes.
              </p>
              
              {/* CTA Button */}
              <div>
                <a 
                  href="#demo"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-white text-black font-medium text-sm hover:bg-gray-100 transition-colors"
                >
                  Get started
                  <ArrowRight className="w-4 h-4" />
                </a>
              </div>
            </div>

            {/* Right Side - Floating Pills */}
            <div className="relative overflow-hidden min-h-[350px] lg:min-h-full">
              {/* Gradient Overlay on left edge */}
              <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-black/90 to-transparent z-10" />
              
              {/* Curved Arc Background */}
              <div 
                className="absolute bottom-[-150px] right-[-100px] w-[500px] h-[400px] rounded-[50%]"
                style={{
                  background: 'linear-gradient(135deg, #0a1628 0%, #000000 50%)',
                  boxShadow: `
                    0 -2px 40px rgba(59, 130, 246, 0.4),
                    0 -4px 80px rgba(139, 92, 246, 0.2),
                    inset 0 0 100px rgba(59, 130, 246, 0.1)
                  `,
                }}
              />
              
              {/* Floating Pills Container */}
              <div className="absolute inset-0 flex flex-col justify-center gap-4 py-8 overflow-hidden">
                {capabilityPills.map((row, rowIndex) => (
                  <div 
                    key={rowIndex}
                    className="flex gap-3 animate-marquee whitespace-nowrap"
                    style={{
                      animationDuration: `${20 + rowIndex * 5}s`,
                      animationDirection: rowIndex % 2 === 0 ? 'normal' : 'reverse',
                      paddingLeft: `${rowIndex * 20}px`,
                    }}
                  >
                    {/* Duplicate pills for seamless loop effect */}
                    {[...row, ...row].map((pill, pillIndex) => (
                      <div
                        key={pillIndex}
                        className="inline-flex items-center px-5 py-3 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 text-white/90 text-sm font-medium hover:bg-white/10 transition-colors shrink-0"
                      >
                        {pill}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Feature Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {featureCards.map((feature, index) => {
            const Icon = feature.icon;
            
            return (
              <div
                key={index}
                className="rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.03] to-transparent p-6 hover:bg-white/[0.05] transition-colors"
              >
                {/* Icon */}
                <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-white" />
                </div>
                
                {/* Title */}
                <h3 className="text-lg font-semibold text-white mb-2">
                  {feature.title}
                </h3>
                
                {/* Description */}
                <p className="text-sm text-gray-400 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
      
      {/* CSS for marquee animation */}
      <style jsx>{`
        @keyframes marquee {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }
        .animate-marquee {
          animation: marquee 20s linear infinite;
        }
      `}</style>
    </section>
  );
}
