"use client";

import { useState } from "react";
import { PixelButton } from "@/components/ui/PixelButton";
import { WaitlistModal } from "@/components/ui/WaitlistModal";

interface PricingTier {
  tier: string;
  name: string;
  features: string[];
  description: string;
  image?: string;
}

const pricingTiers: PricingTier[] = [
  {
    tier: "NotSudo",
    name: "Get started with real coding tasks.",
    features: [
      "15 tasks per day",
      "3 concurrent tasks",
      "Access Opus 4.5, Codex, Gemini 2.5",
    ],
    description: "",
  },
  {
    tier: "NotSudo in Pro",
    name: "For devs who ship daily and want to stay in the flow.",
    features: [
      "100 tasks per day, enough to run NotSudo throughout your coding day",
      "15 concurrent tasks, so you can run multiple threads in parallel",
      "Access latest models: Opus 4.5, Codex, Gemini 3",
    ],
    description: "",
  },
  {
    tier: "NotSudo in Ultra",
    name: "For builders who run agents at scale.",
    features: [
      "300 tasks per day to handle the most demanding development cycles",
      "60 concurrent tasks, built for massively parallel workflows",
      "Priority access: Opus 4.5, Codex, Gemini 3",
    ],
    description: "",
  },
];

export function PricingSection() {
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);

  return (
    <section id="pricing" className="relative py-24 px-4 bg-black border-t-2 border-orange-500/30">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-2 text-lg font-retro-body text-orange-500 border-2 border-orange-500/50 mb-6 uppercase tracking-wider">
            [ PRICING ]
          </span>
          <h2 className="font-retro-heading text-xl md:text-2xl lg:text-3xl text-white mb-6 leading-relaxed tracking-wide uppercase">
            Find the NotSudo plan that
            <br />
            fits your workflow
          </h2>

          <p className="text-gray-400 max-w-2xl mx-auto font-retro-body text-xl leading-relaxed">
            NotSudo scales with how you build, from quick fixes to fully async,
            multi-agent development. Choose the plan that gives you the speed,
            throughput, and model access you need.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {pricingTiers.map((tier, index) => (
            <div
              key={index}
              className="bg-black border border-gray-800 p-8 flex flex-col h-full hover:border-orange-500/50 transition-colors group"
            >
              <h3 className="text-xl font-retro-body text-orange-500 mb-4 uppercase tracking-wider">
                [ {tier.tier} ]
              </h3>

              <p className="text-gray-400 font-retro-body text-lg mb-8 min-h-[60px]">
                {tier.name}
              </p>

              <ul className="space-y-4 mb-8 flex-1">
                {tier.features.map((feature, featureIndex) => (
                  <li
                    key={featureIndex}
                    className="flex items-start gap-3 text-base text-gray-300 font-retro-body leading-relaxed"
                  >
                    <span className="text-orange-500 mt-1">►</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <PixelButton onClick={() => setIsWaitlistOpen(true)} className="w-full">
                Join Waitlist
              </PixelButton>
            </div>
          ))}
        </div>
      </div>

      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </section>
  );
}
