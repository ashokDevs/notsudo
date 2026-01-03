"use client";

import { useState } from "react";
import { Zap, Shield, Layers, Coffee } from "lucide-react";
import { PixelButton } from "@/components/ui/PixelButton";
import { WaitlistModal } from "@/components/ui/WaitlistModal";

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
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);

  return (
    <section className="relative py-24 px-4 bg-black overflow-hidden border-t-2 border-orange-500/30">
      <div className="relative z-10 max-w-7xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-3 h-3 bg-cyan-500" />
          <span className="text-lg font-retro-body text-cyan-500 uppercase tracking-wider">
            [ CAPABILITIES ]
          </span>
        </div>

        <div className="relative border-2 border-cyan-500/50 bg-black/80 overflow-hidden min-h-[450px] mb-6 retro-scanlines">
          <div className="grid grid-cols-1 lg:grid-cols-2 h-full min-h-[450px]">
            <div className="relative z-10 p-8 lg:p-12 flex flex-col justify-center">
              <h2 className="font-retro-heading text-xl lg:text-2xl text-white mb-4 leading-relaxed uppercase tracking-wider">
                Fix issues,
                <br />
                <span className="text-cyan-400">ship PRs faster</span>
              </h2>
              <p className="text-xl font-retro-body text-gray-400 mb-8">
                Tag @notsudo on any GitHub issue and get a working PR in minutes.
              </p>
              
              <div>
                <PixelButton onClick={() => setIsWaitlistOpen(true)} size="md">
                  Join Waitlist
                </PixelButton>
              </div>
            </div>

            <div className="relative overflow-hidden min-h-[350px] lg:min-h-full">
              <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-black to-transparent z-10" />
              
              <div 
                className="absolute bottom-[-150px] right-[-100px] w-[500px] h-[400px] rounded-[50%]"
                style={{
                  background: 'linear-gradient(135deg, #0a1628 0%, #000000 50%)',
                  boxShadow: `
                    0 -2px 40px rgba(6, 182, 212, 0.4),
                    0 -4px 80px rgba(6, 182, 212, 0.2),
                    inset 0 0 100px rgba(6, 182, 212, 0.1)
                  `,
                }}
              />
              
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
                    {[...row, ...row].map((pill, pillIndex) => (
                      <div
                        key={pillIndex}
                        className="inline-flex items-center px-5 py-3 border-2 border-green-500/50 bg-black/80 text-green-400 font-retro-body text-lg uppercase tracking-wider hover:border-green-400 hover:bg-green-500/10 transition-colors shrink-0"
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

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {featureCards.map((feature, index) => {
            const Icon = feature.icon;
            
            return (
              <div
                key={index}
                className="border-2 border-orange-500/30 bg-black/80 p-6 hover:border-orange-500 transition-colors retro-card"
              >
                <div className="w-12 h-12 border-2 border-orange-500 flex items-center justify-center mb-4">
                  <Icon className="w-6 h-6 text-orange-500" />
                </div>
                
                <h3 className="text-lg font-retro-body text-white mb-2 uppercase tracking-wider">
                  {feature.title}
                </h3>
                
                <p className="text-base font-retro-body text-gray-500 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
      
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

      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </section>
  );
}
