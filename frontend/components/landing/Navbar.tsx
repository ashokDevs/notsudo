"use client";

import { useState, useEffect } from "react";
import { Menu, X } from "lucide-react";
import { PixelButton } from "@/components/ui/PixelButton";
import { WaitlistModal } from "@/components/ui/WaitlistModal";

export function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleWaitlistClick = () => {
    setIsMobileMenuOpen(false);
    setIsWaitlistOpen(true);
  };

  return (
    <>
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled
            ? "bg-black/80 backdrop-blur-xl border-b border-orange-500/20"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <a href="/" className="text-xl font-retro-heading text-orange-500 tracking-wider hover:retro-glow-orange transition-all">
              NotSudo
            </a>

            <div className="hidden md:flex items-center gap-8">
              <a
                href="#pricing"
                className="text-lg font-retro-body text-gray-400 hover:text-orange-500 transition-colors uppercase tracking-wider"
              >
                [ Plans ]
              </a>
              <PixelButton onClick={handleWaitlistClick} size="sm">
                Join Waitlist
              </PixelButton>
            </div>

            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden text-orange-500 p-2"
              aria-label="Toggle menu"
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </nav>

      <div
        className={`fixed inset-0 z-40 bg-black/95 backdrop-blur-xl transition-all duration-300 md:hidden retro-scanlines ${
          isMobileMenuOpen
            ? "opacity-100 pointer-events-auto"
            : "opacity-0 pointer-events-none"
        }`}
      >
        <div className="flex flex-col items-center justify-center h-full gap-8">
          <a
            href="#pricing"
            onClick={() => setIsMobileMenuOpen(false)}
            className="text-2xl font-retro-body text-orange-500 hover:retro-glow-orange transition-all uppercase tracking-wider"
          >
            [ Plans ]
          </a>
          <PixelButton onClick={handleWaitlistClick} size="md">
            Join Waitlist
          </PixelButton>
        </div>
      </div>

      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </>
  );
}
