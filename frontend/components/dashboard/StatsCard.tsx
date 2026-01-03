"use client";

import { ReactNode } from "react";

interface StatsCardProps {
  title: string;
  value: number | string;
  icon?: ReactNode;
  variant?: "default" | "processing" | "completed" | "failed";
}

const variantStyles = {
  default: "border-white/10",
  processing: "border-amber-500/30 bg-amber-500/5",
  completed: "border-green-500/30 bg-green-500/5",
  failed: "border-red-500/30 bg-red-500/5",
};

const iconVariantStyles = {
  default: "bg-white/10 text-white",
  processing: "bg-amber-500/20 text-amber-500",
  completed: "bg-green-500/20 text-green-500",
  failed: "bg-red-500/20 text-red-500",
};

export function StatsCard({ title, value, icon, variant = "default" }: StatsCardProps) {
  return (
    <div className={`relative border ${variantStyles[variant]} bg-black/50 p-6 overflow-hidden`}>
      {/* Grid background pattern */}
      <div 
        className="absolute inset-0 opacity-30"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '20px 20px',
        }}
      />
      
      {/* Corner markers */}
      <span className="absolute top-2 left-2 text-white/20 font-mono text-xs">+</span>
      <span className="absolute top-2 right-2 text-white/20 font-mono text-xs">+</span>
      <span className="absolute bottom-2 left-2 text-white/20 font-mono text-xs">+</span>
      <span className="absolute bottom-2 right-2 text-white/20 font-mono text-xs">+</span>
      
      <div className="relative z-10 flex items-start justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-gray-500 mb-2">
            {title}
          </p>
          <p className="font-mono text-3xl font-bold text-white">
            {value}
          </p>
        </div>
        {icon && (
          <div className={`p-3 rounded-lg ${iconVariantStyles[variant]}`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
