"use client";

import { useState } from "react";
import { PixelButton } from "./PixelButton";

interface WaitlistModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function WaitlistModal({ isOpen, onClose }: WaitlistModalProps) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim()) {
      setStatus("error");
      setMessage("Please enter your email");
      return;
    }

    setStatus("loading");
    setMessage("");

    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });

      const data = await response.json();

      if (response.ok) {
        setStatus("success");
        setMessage(data.message || "You're on the list!");
        setEmail("");
        // Auto-close after success
        setTimeout(() => {
          onClose();
          setStatus("idle");
          setMessage("");
        }, 2000);
      } else {
        setStatus("error");
        setMessage(data.error || "Something went wrong");
      }
    } catch {
      setStatus("error");
      setMessage("Network error. Please try again.");
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="relative w-full max-w-md mx-4 p-8 bg-black border-2 border-orange-500 shadow-[0_0_30px_rgba(249,115,22,0.3)]">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-white text-2xl font-bold"
        >
          ×
        </button>

        {/* Header */}
        <div className="text-center mb-8">
          <h2 className="font-retro-heading text-xl md:text-2xl text-orange-500 uppercase tracking-wider mb-2">
            Join Waitlist
          </h2>
          <p className="text-gray-400 font-retro-body">
            Get early access to NotSudo
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              disabled={status === "loading" || status === "success"}
              className="w-full px-4 py-3 bg-gray-900 border-2 border-gray-700 text-white font-retro-body placeholder-gray-500 focus:border-orange-500 focus:outline-none transition-colors disabled:opacity-50"
            />
          </div>

          {/* Status message */}
          {message && (
            <p
              className={`text-center font-retro-body text-sm ${
                status === "success" ? "text-green-500" : "text-red-500"
              }`}
            >
              {message}
            </p>
          )}

          {/* Submit button */}
          <div className="flex justify-center">
            <PixelButton
              onClick={() => {}}
              variant={status === "success" ? "green" : "orange"}
            >
              {status === "loading" ? "Submitting..." : status === "success" ? "✓ Joined!" : "Submit"}
            </PixelButton>
          </div>
        </form>

        {/* Decorative corners */}
        <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-orange-500" />
        <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-orange-500" />
        <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-orange-500" />
        <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-orange-500" />
      </div>
    </div>
  );
}
