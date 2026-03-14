"use client";

import { useState, useEffect } from "react";
import { Cpu, ChevronDown, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface AIModel {
  id: string;
  name: string;
  provider: string;
}

interface ModelSelectorProps {
  onSelect: (modelId: string) => void;
  selectedModelId?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function ModelSelector({ onSelect, selectedModelId }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [models, setModels] = useState<AIModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/models`);
        if (res.ok) {
          const data = await res.json();
          setModels(data.models || []);
        }
      } catch {
        // Silently handle fetch errors - user will see "Select model" fallback
      } finally {
        setIsLoading(false);
      }
    };
    fetchModels();
  }, []);

  const selectedModel = models.find(m => m.id === selectedModelId);

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/50 border border-zinc-800 rounded-lg hover:bg-zinc-800 transition-all group min-w-[160px]"
      >
        <div className="w-5 h-5 rounded bg-orange-500/10 flex items-center justify-center border border-orange-500/20 text-orange-500">
           <Cpu className="w-3.5 h-3.5" />
        </div>
        <span className="text-sm font-medium text-zinc-300 truncate text-left flex-1">
          {selectedModel ? selectedModel.name : (isLoading ? "Loading..." : "Select model")}
        </span>
        <ChevronDown className={cn("w-4 h-4 text-zinc-500 transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && !isLoading && (
        <>
          <div className="fixed inset-0 z-[60]" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 mt-2 w-64 bg-[#121214] border border-zinc-800/80 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[70] overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="p-2 space-y-0.5">
              {models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => {
                    onSelect(model.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    "w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg text-sm transition-all text-left",
                    selectedModelId === model.id 
                      ? "text-zinc-100" 
                      : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100"
                  )}
                >
                  <div className="min-w-0">
                    <div className="font-medium truncate">{model.name}</div>
                    <div className="text-[10px] opacity-40 uppercase tracking-widest font-bold">{model.provider}</div>
                  </div>
                  {selectedModelId === model.id && <Check className="w-4 h-4 text-zinc-100 shrink-0" />}
                </button>
              ))}
            </div>
            
            {models.length === 0 && (
              <div className="p-8 text-center text-xs text-zinc-600 font-medium">
                No models available
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
