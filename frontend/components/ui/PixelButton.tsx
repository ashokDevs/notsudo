"use client";

interface PixelButtonProps {
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
  variant?: "orange" | "green" | "gray";
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function PixelButton({ 
  children, 
  href, 
  onClick,
  variant = "orange",
  size = "md",
  className = ""
}: PixelButtonProps) {
  const variants = {
    orange: {
      shadow: "bg-orange-900",
      body: "bg-gradient-to-b from-orange-400 via-orange-500 to-orange-600 border-orange-400",
      highlight: "bg-orange-300/50",
      text: "text-black",
    },
    green: {
      shadow: "bg-green-900",
      body: "bg-gradient-to-b from-green-400 via-green-500 to-green-600 border-green-400",
      highlight: "bg-green-300/50",
      text: "text-black",
    },
    gray: {
      shadow: "bg-gray-900",
      body: "bg-gradient-to-b from-gray-500 via-gray-600 to-gray-700 border-gray-400",
      highlight: "bg-gray-400/50",
      text: "text-white",
    },
  };

  const sizes = {
    sm: "py-2 px-4 text-base",
    md: "py-3 px-6 text-lg",
    lg: "py-4 px-8 text-xl",
  };

  const v = variants[variant];
  const s = sizes[size];

  const content = (
    <>
      {/* Bottom shadow layer (darkest) */}
      <div className={`absolute inset-0 ${v.shadow} translate-y-2 rounded-sm`} />
      
      {/* Main button body */}
      <div className={`relative ${v.body} ${s} rounded-sm border-2`}>
        {/* Inner highlight (top) */}
        <div className={`absolute inset-x-1 top-1 h-1 ${v.highlight} rounded-sm`} />
        
        {/* Text */}
        <span className={`relative ${v.text} font-bold font-retro-body uppercase tracking-wider`}>
          {children}
        </span>
      </div>
    </>
  );

  if (href) {
    return (
      <a
        href={href}
        className={`relative inline-block text-center transition-all active:translate-y-1 hover:brightness-110 ${className}`}
      >
        {content}
      </a>
    );
  }

  return (
    <button
      onClick={onClick}
      className={`relative inline-block text-center transition-all active:translate-y-1 hover:brightness-110 ${className}`}
    >
      {content}
    </button>
  );
}
