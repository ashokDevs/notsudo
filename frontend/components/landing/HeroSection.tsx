"use client";

import { useEffect, useRef, useState } from "react";
import { PixelButton } from "@/components/ui/PixelButton";
import { WaitlistModal } from "@/components/ui/WaitlistModal";



// Types for our retro game entities
interface Point {
  x: number;
  y: number;
}

interface Bug {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  spawnTime: number;
}

interface Rocket {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface Particle extends Point {
  vx: number;
  vy: number;
  life: number;
  color: string;
  size: number;
}

const RetroBackground = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let bugs: Bug[] = [];
    let rockets: Rocket[] = [];
    let particles: Particle[] = [];
    let lastRocketTime = 0;
    let nextId = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener("resize", resize);
    resize();

    // Bug visual pattern (5x5 invader style)
    const bugPattern = [
      [1, 0, 1, 0, 1],
      [0, 1, 1, 1, 0],
      [1, 1, 0, 1, 1],
      [1, 0, 1, 0, 1],
      [1, 0, 0, 0, 1]
    ];

    // Rocket visual pattern
    const rocketPattern = [
      [0, 1, 0],
      [1, 1, 1],
      [0, 1, 0],
      [0, 1, 0]
    ];

    const drawPixelArt = (ctx: CanvasRenderingContext2D, cx: number, cy: number, color: string, pattern: number[][], scale: number) => {
      ctx.fillStyle = color;
      const rows = pattern.length;
      const cols = pattern[0].length;
      const width = cols * scale;
      const height = rows * scale;
      const startX = cx - width / 2;
      const startY = cy - height / 2;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          if (pattern[r][c]) {
            ctx.fillRect(startX + c * scale, startY + r * scale, scale, scale);
          }
        }
      }
    };

    const spawnBug = () => {
      const margin = 50;
      let x = 0, y = 0;
      let safe = false;
      let attempts = 0;
      
      const excludeWidth = 900;
      const excludeHeight = 500;
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      while (!safe && attempts < 50) {
        x = margin + Math.random() * (canvas.width - 2 * margin);
        y = margin + Math.random() * (canvas.height - 2 * margin);
        
        const inExcludedZone = 
          x > centerX - excludeWidth / 2 && 
          x < centerX + excludeWidth / 2 && 
          y > centerY - excludeHeight / 2 && 
          y < centerY + excludeHeight / 2;

        if (!inExcludedZone) {
          safe = true;
        }
        attempts++;
      }

      bugs.push({
        id: nextId++,
        x,
        y,
        width: 40,
        height: 40,
        spawnTime: Date.now(),
      });
    };

    const spawnRocket = () => {
      if (bugs.length === 0) return;
      const target = bugs[Math.floor(Math.random() * bugs.length)];
      
      let startX, startY;
      if (Math.random() < 0.5) {
        startX = Math.random() < 0.5 ? -20 : canvas.width + 20;
        startY = Math.random() * canvas.height;
      } else {
        startX = Math.random() * canvas.width;
        startY = Math.random() < 0.5 ? -20 : canvas.height + 20;
      }

      const speed = 8;
      const dx = target.x - startX;
      const dy = target.y - startY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      rockets.push({
        id: nextId++,
        x: startX,
        y: startY,
        vx: (dx / dist) * speed,
        vy: (dy / dist) * speed,
      });
    };

    const explode = (x: number, y: number) => {
      for (let i = 0; i < 15; i++) {
        particles.push({
          x,
          y,
          vx: (Math.random() - 0.5) * 12,
          vy: (Math.random() - 0.5) * 12,
          life: 1.0,
          color: Math.random() > 0.5 ? '#f97316' : '#ef4444',
          size: Math.random() * 6 + 4,
        });
      }
    };

    const loop = (time: number) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (bugs.length < 3) {
        if (Math.random() < 0.05) {
            spawnBug();
        }
      }

      if (time - lastRocketTime > 1200 && bugs.length > 0) {
        spawnRocket();
        lastRocketTime = time;
      }

      bugs.forEach(bug => {
        bug.x += (Math.random() - 0.5) * 0.8;
        bug.y += (Math.random() - 0.5) * 0.8;

        ctx.strokeStyle = '#22c55e';
        ctx.lineWidth = 2;
        ctx.strokeRect(bug.x - 25, bug.y - 25, 50, 50);

        drawPixelArt(ctx, bug.x, bug.y, '#22c55e', bugPattern, 6);
      });

      for (let i = rockets.length - 1; i >= 0; i--) {
        const r = rockets[i];
        r.x += r.vx;
        r.y += r.vy;

        drawPixelArt(ctx, r.x, r.y, '#f97316', rocketPattern, 4);

        let hit = false;
        for (let j = bugs.length - 1; j >= 0; j--) {
          const b = bugs[j];
          const dx = b.x - r.x;
          const dy = b.y - r.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 35) {
            explode(b.x, b.y);
            bugs.splice(j, 1);
            hit = true;
            break;
          }
        }

        if (hit) {
          rockets.splice(i, 1);
        } else {
          if (r.x < -50 || r.x > canvas.width + 50 || r.y < -50 || r.y > canvas.height + 50) {
             rockets.splice(i, 1);
          }
        }
      }

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.life -= 0.03;

        if (p.life <= 0) {
          particles.splice(i, 1);
        } else {
          ctx.globalAlpha = p.life;
          ctx.fillStyle = p.color;
          ctx.fillRect(p.x, p.y, p.size, p.size);
          ctx.globalAlpha = 1.0;
        }
      }

      animationFrameId = requestAnimationFrame(loop);
    };

    animationFrameId = requestAnimationFrame(loop);

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 z-0 pointer-events-none opacity-60" />;
};

export function HeroSection() {
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-4 bg-black overflow-hidden retro-scanlines">
      <RetroBackground />

      <div className="relative z-10 text-center max-w-5xl mx-auto pointer-events-none">
        <h1 className="fade-in-up-delay-1 font-retro-heading text-2xl md:text-4xl lg:text-5xl font-bold text-white mb-8 leading-loose tracking-wide uppercase">
          Just Assign. We&apos;ll Ship.
        </h1>

        <div className="fade-in-up-delay-2 flex flex-wrap justify-center gap-3 max-w-3xl mx-auto mb-12 font-mono text-sm md:text-base">
          {["Works 24/7", "Multiple AI Models", "GitHub Native", "Enterprise Secure"].map((tag, i) => (
            <span key={i} className="px-3 py-1 border border-gray-700 rounded-full text-gray-300 bg-gray-900/50">
              {tag}
            </span>
          ))}
        </div>

        <div className="fade-in-up-delay-3 flex flex-col items-center gap-8 mb-16 pointer-events-auto">
          <PixelButton onClick={() => setIsWaitlistOpen(true)} size="lg">
            JOIN WAITLIST
          </PixelButton>

          <div className="max-w-md mx-auto text-center mt-8">
            <p className="text-xl text-white font-mono leading-relaxed">
              Your GitHub issues, resolved autonomously.
            </p>
          </div>
        </div>
      </div>

      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </section>
  );
}
