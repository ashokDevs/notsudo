"use client";

import { useState, useCallback, useRef, useEffect } from "react";

// Grid configuration
const GRID_COLS = 20;
const GRID_ROWS = 12;

interface CellState {
  opacity: number;
}

export function HeroSection() {
  const [cellStates, setCellStates] = useState<Record<number, CellState>>({});
  const fadeTimeouts = useRef<Record<number, NodeJS.Timeout>>({});

  const handleMouseEnter = useCallback((index: number) => {
    // Clear any existing timeout for this cell
    if (fadeTimeouts.current[index]) {
      clearTimeout(fadeTimeouts.current[index]);
    }
    
    // Set cell to full opacity
    setCellStates(prev => ({
      ...prev,
      [index]: { opacity: 1 }
    }));
  }, []);

  const handleMouseLeave = useCallback((index: number) => {
    // Start fade out animation
    const fadeSteps = [0.8, 0.6, 0.4, 0.2, 0];
    let stepIndex = 0;
    
    const fadeStep = () => {
      setCellStates(prev => ({
        ...prev,
        [index]: { opacity: fadeSteps[stepIndex] }
      }));
      
      stepIndex++;
      if (stepIndex < fadeSteps.length) {
        fadeTimeouts.current[index] = setTimeout(fadeStep, 150);
      } else {
        // Remove from state when fully faded
        setCellStates(prev => {
          const newState = { ...prev };
          delete newState[index];
          return newState;
        });
      }
    };
    
    fadeTimeouts.current[index] = setTimeout(fadeStep, 100);
  }, []);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      Object.values(fadeTimeouts.current).forEach(timeout => clearTimeout(timeout));
    };
  }, []);

  const getCellStyle = (index: number) => {
    const state = cellStates[index];
    if (!state) return {};
    
    return {
      backgroundColor: `rgba(249, 115, 22, ${state.opacity * 0.5})`,
    };
  };

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-4 bg-black overflow-hidden">
      {/* Grid Background */}
      <div className="absolute inset-0 z-0">
        <div 
          className="w-full h-full grid"
          style={{
            gridTemplateColumns: `repeat(${GRID_COLS}, 1fr)`,
            gridTemplateRows: `repeat(${GRID_ROWS}, 1fr)`,
          }}
        >
          {Array.from({ length: GRID_COLS * GRID_ROWS }).map((_, index) => (
            <div
              key={index}
              className="border border-white/10 transition-colors duration-300"
              style={getCellStyle(index)}
              onMouseEnter={() => handleMouseEnter(index)}
              onMouseLeave={() => handleMouseLeave(index)}
            />
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="relative z-10 text-center max-w-5xl mx-auto pointer-events-none">
        {/* Main Headline */}
        <h1 className="fade-in-up-delay-1 font-mono text-5xl md:text-7xl lg:text-8xl font-bold text-white mb-8 leading-tight tracking-tighter uppercase">
          Your Junior Dev
          <br />
          <span className="inline-block border-2 border-orange-500 px-4 py-2 mt-4">
            That Never Sleeps
          </span>
        </h1>

        {/* Subheadline */}
        <p className="fade-in-up-delay-2 text-lg md:text-xl lg:text-2xl text-gray-400 max-w-2xl mx-auto mb-12 font-mono">
          An AI coding agent that works 24/7 on your GitHub issues.
          <br />
          From bug fixes to features – done in minutes, not days.
        </p>

        {/* CTA Button */}
        <div className="fade-in-up-delay-3 flex justify-center items-center mb-16 pointer-events-auto">
          <a
            href="/login"
            className="group inline-flex items-center gap-2 px-8 py-4 bg-white text-black font-mono text-base font-medium hover:bg-gray-100 transition-all duration-300 border border-white"
          >
            START FOR FREE
          </a>
        </div>
      </div>
    </section>
  );
}
