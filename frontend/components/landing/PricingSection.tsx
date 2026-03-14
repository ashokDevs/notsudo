"use client";

import { useState } from "react";
import { PixelButton } from "@/components/ui/PixelButton";
import { WaitlistModal } from "@/components/ui/WaitlistModal";
import { authClient, useSession } from "@/lib/auth-client";
import { useRouter } from "next/navigation";

interface PricingTier {
  tier: string;
  name: string;
  features: string[];
  description: string;
  price: number | string;
  originalPrice?: number;
  discount?: string;
  image?: string;
}

const pricingTiers: PricingTier[] = [
  {
    tier: "Basic",
    name: "Get started with real coding tasks.",
    features: [
      "15 tasks per day",
      "3 concurrent tasks",
      "Access Opus 4.5, Codex, Gemini 2.5",
    ],
    price: 0,
    description: "",
  },
  {
    tier: "Pro",
    name: "For devs who ship daily and want to stay in the flow.",
    features: [
      "100 tasks per day, enough to run NotSudo throughout your coding day",
      "15 concurrent tasks, so you can run multiple threads in parallel",
      "Access latest models: Opus 4.5, Codex, Gemini 3",
    ],
    price: 49,
    originalPrice: 98,
    discount: "50% OFF",
    description: "",
  },
  {
    tier: "Ultra",
    name: "For builders who run agents at scale.",
    features: [
      "300 tasks per day to handle the most demanding development cycles",
      "60 concurrent tasks, built for massively parallel workflows",
      "Priority access: Opus 4.5, Codex, Gemini 3",
    ],
    price: 100,
    originalPrice: 200,
    discount: "50% OFF",
    description: "",
  },
];

export function PricingSection() {
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);
  const { data: session } = useSession();
  const router = useRouter();

  const handleCheckout = async (tier: string) => {
    if (tier === "Basic") {
      setIsWaitlistOpen(true);
      return;
    }

    if (!session) {
      router.push("/login?callbackUrl=#pricing");
      return;
    }

    try {
      // @ts-ignore - dodopayments is added by the plugin
      const { data, error } = await authClient.dodopayments.checkout({
        slug: tier.toLowerCase(),
      });

      if (error) {
        setIsWaitlistOpen(true);
        return;
      }

      if (data?.url) {
        window.location.href = data.url;
      }
    } catch {
      setIsWaitlistOpen(true);
    }
  };

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
              className="bg-black border border-gray-800 p-8 flex flex-col h-full hover:border-orange-500/50 transition-colors group relative overflow-hidden"
            >
              {tier.discount && (
                <div className="absolute top-0 right-0 bg-orange-500 text-black font-retro-body text-xs px-3 py-1 uppercase tracking-tighter">
                  {tier.discount}
                </div>
              )}
              
              <h3 className="text-xl font-retro-body text-orange-500 mb-4 uppercase tracking-wider">
                [ {tier.tier} ]
              </h3>

              <div className="mb-6">
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-retro-heading text-white">
                    {tier.price === 0 ? "FREE" : `$${tier.price}`}
                  </span>
                  {tier.originalPrice && (
                    <span className="text-xl text-gray-500 line-through font-retro-body">
                      ${tier.originalPrice}
                    </span>
                  )}
                </div>
                {tier.price !== 0 && (
                  <span className="text-gray-500 font-retro-body text-sm">/month</span>
                )}
              </div>

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

              <PixelButton onClick={() => handleCheckout(tier.tier)} className="w-full">
                {tier.tier === "Basic" ? "Join Waitlist" : "Get Started"}
              </PixelButton>
            </div>
          ))}
        </div>
      </div>

      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </section>
  );
}
