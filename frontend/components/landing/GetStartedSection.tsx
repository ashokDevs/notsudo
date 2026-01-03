"use client";

import { useState } from "react";
import { PixelButton } from "@/components/ui/PixelButton";
import { WaitlistModal } from "@/components/ui/WaitlistModal";

export function GetStartedSection() {
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);

  return (
    <section className="relative bg-black border-t-2 border-orange-500/30">
      <div className="border-b-2 border-orange-500/30">
        <div className="max-w-6xl mx-auto px-4 py-24">
          <div className="text-center">
            <h2 className="font-retro-heading text-xl md:text-2xl lg:text-3xl text-white mb-8 leading-relaxed tracking-wide uppercase">
              GET STARTED{" "}
              <span className="inline-block border-4 border-green-500 px-4 py-2 retro-box-glow-green">
                TODAY
              </span>
            </h2>

            <p className="text-gray-400 max-w-lg mx-auto mb-10 font-retro-body text-xl">
              Stop letting issues pile up. Tag @notsudo and
              <br />
              get working pull requests in minutes, not days.
            </p>

            <div className="flex justify-center">
              <PixelButton onClick={() => setIsWaitlistOpen(true)} variant="green" size="lg">
                Join Waitlist
              </PixelButton>
            </div>
          </div>
        </div>
      </div>

      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </section>
  );
}
