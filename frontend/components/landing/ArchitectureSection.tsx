"use client";

import { useEffect, useState } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Position,
  MarkerType,
  Handle,
  ConnectionLineType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion } from "framer-motion";
import {
  Github,
  Bot,
  Server,
  Container,
  GitPullRequest,
  Lock,
  Terminal,
} from "lucide-react";

// ==================== Custom Node Components ====================

// Simple Node with icon and label
function SimpleNode({ data }: { data: { label: string; icon: React.ElementType; color: string } }) {
  const Icon = data.icon;
  const colorClasses: Record<string, { border: string; icon: string }> = {
    blue: { border: "border-blue-500/50", icon: "text-blue-400" },
    purple: { border: "border-purple-500/50", icon: "text-purple-400" },
    amber: { border: "border-amber-500/50", icon: "text-amber-400" },
    emerald: { border: "border-emerald-500/50", icon: "text-emerald-400" },
    green: { border: "border-green-500/50", icon: "text-green-400" },
  };
  const colors = colorClasses[data.color] || colorClasses.blue;

  return (
    <div className="relative">
      <Handle type="source" position={Position.Right} className="!bg-white/50 !w-2 !h-2 !border-0" />
      <Handle type="target" position={Position.Left} className="!bg-white/50 !w-2 !h-2 !border-0" />
      <Handle type="source" position={Position.Top} id="top" className="!bg-white/50 !w-2 !h-2 !border-0" />
      <Handle type="target" position={Position.Bottom} id="bottom" className="!bg-white/50 !w-2 !h-2 !border-0" />
      <div className={`px-5 py-4 rounded-xl border ${colors.border} min-w-[120px]`}>
        <div className="flex flex-col items-center gap-2">
          <div className={`w-11 h-11 rounded-xl border ${colors.border} flex items-center justify-center`}>
            <Icon className={`w-5 h-5 ${colors.icon}`} />
          </div>
          <div className="text-sm font-medium text-white">{data.label}</div>
        </div>
      </div>
    </div>
  );
}

// Security Node - Docker Sandbox with badge
function SecurityNode({ data }: { data: { label: string; icon: React.ElementType } }) {
  const Icon = data.icon;
  return (
    <div className="relative">
      <Handle type="source" position={Position.Right} className="!bg-white/50 !w-2 !h-2 !border-0" />
      <Handle type="target" position={Position.Left} className="!bg-white/50 !w-2 !h-2 !border-0" />
      
      <div className="relative px-5 py-4 rounded-xl border-2 border-emerald-500/60 min-w-[140px]">
        {/* Security Badge */}
        <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full bg-emerald-500 text-[9px] font-bold text-white flex items-center gap-1">
          <Lock className="w-2.5 h-2.5" />
          ISOLATED
        </div>
        
        <div className="flex flex-col items-center gap-2 mt-1">
          <div className="w-11 h-11 rounded-xl border border-emerald-500/50 flex items-center justify-center">
            <Icon className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-sm font-medium text-white">{data.label}</div>
        </div>
      </div>
    </div>
  );
}

// Node types registry
const nodeTypes = {
  simple: SimpleNode,
  security: SecurityNode,
};

// ==================== Architecture Layout - Circular Flow ====================

const architectureNodes: Node[] = [
  {
    id: "github",
    type: "simple",
    position: { x: 0, y: 100 },
    data: { label: "GitHub", icon: Github, color: "blue" },
  },
  {
    id: "backend",
    type: "simple",
    position: { x: 180, y: 100 },
    data: { label: "Flask API", icon: Server, color: "purple" },
  },
  {
    id: "ai",
    type: "simple",
    position: { x: 360, y: 100 },
    data: { label: "AI Engine", icon: Bot, color: "amber" },
  },
  {
    id: "sandbox",
    type: "security",
    position: { x: 540, y: 95 },
    data: { label: "Docker Sandbox", icon: Container },
  },
  {
    id: "tests",
    type: "simple",
    position: { x: 740, y: 100 },
    data: { label: "Run Tests", icon: Terminal, color: "emerald" },
  },
  {
    id: "pr",
    type: "simple",
    position: { x: 920, y: 100 },
    data: { label: "Pull Request", icon: GitPullRequest, color: "green" },
  },
];

const architectureEdges: Edge[] = [
  {
    id: "e1",
    source: "github",
    target: "backend",
    animated: true,
    style: { stroke: "#60a5fa", strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#60a5fa", width: 15, height: 15 },
  },
  {
    id: "e2",
    source: "backend",
    target: "ai",
    animated: true,
    style: { stroke: "#a855f7", strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#a855f7", width: 15, height: 15 },
  },
  {
    id: "e3",
    source: "ai",
    target: "sandbox",
    animated: true,
    style: { stroke: "#f59e0b", strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#f59e0b", width: 15, height: 15 },
  },
  {
    id: "e4",
    source: "sandbox",
    target: "tests",
    animated: true,
    style: { stroke: "#10b981", strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#10b981", width: 15, height: 15 },
  },
  {
    id: "e5",
    source: "tests",
    target: "pr",
    animated: true,
    style: { stroke: "#22c55e", strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e", width: 15, height: 15 },
  },
  // Loop back: PR → GitHub
  {
    id: "e6-loop",
    source: "pr",
    target: "github",
    sourceHandle: "top",
    targetHandle: "top",
    animated: true,
    type: "smoothstep",
    style: { stroke: "#60a5fa", strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#60a5fa", width: 15, height: 15 },
    label: "Merged",
    labelStyle: { fill: "#60a5fa", fontSize: 10, fontWeight: 500 },
    labelBgStyle: { fill: "#000", fillOpacity: 0.9 },
    labelBgPadding: [4, 4] as [number, number],
    labelBgBorderRadius: 4,
  },
];

// ==================== Mobile View ====================

function MobileArchitectureView() {
  const items = [
    { icon: Github, label: "GitHub", color: "blue" },
    { icon: Server, label: "Flask API", color: "purple" },
    { icon: Bot, label: "AI Engine", color: "amber" },
    { icon: Container, label: "Docker Sandbox", color: "emerald", security: true },
    { icon: Terminal, label: "Run Tests", color: "emerald" },
    { icon: GitPullRequest, label: "Pull Request", color: "green" },
  ];

  return (
    <div className="py-6 px-4">
      <div className="flex flex-col items-center gap-2">
        {items.map((item, index) => {
          const Icon = item.icon;
          const colorClasses: Record<string, string> = {
            blue: "border-blue-500/50 text-blue-400",
            purple: "border-purple-500/50 text-purple-400",
            amber: "border-amber-500/50 text-amber-400",
            emerald: "border-emerald-500/50 text-emerald-400",
            green: "border-green-500/50 text-green-400",
          };
          return (
            <div key={index} className="relative w-full max-w-[200px]">
              <div className={`
                flex items-center gap-3 p-3 rounded-xl border
                ${item.security ? "border-emerald-500/60 border-2" : "border-white/10"}
              `}>
                {item.security && (
                  <div className="absolute -top-2 right-3 px-2 py-0.5 rounded-full bg-emerald-500 text-[8px] font-bold text-white flex items-center gap-1">
                    <Lock className="w-2 h-2" />
                    ISOLATED
                  </div>
                )}
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${colorClasses[item.color]?.split(" ")[0]}`}>
                  <Icon className={`w-4 h-4 ${colorClasses[item.color]?.split(" ")[1]}`} />
                </div>
                <span className="text-sm font-medium text-white">{item.label}</span>
              </div>
              
              {index < items.length - 1 && (
                <div className="flex justify-center py-1">
                  <div className="w-0.5 h-2 bg-white/20" />
                </div>
              )}
            </div>
          );
        })}
        
        {/* Loop back indicator */}
        <div className="flex items-center gap-2 mt-2 text-xs text-blue-400">
          <span>↺ Merged back to GitHub</span>
        </div>
      </div>
    </div>
  );
}

// ==================== Main Component ====================

export function ArchitectureSection() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 1024);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  return (
    <section className="relative py-24 px-4 bg-black overflow-hidden border-t-2 border-orange-500/30">
      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Section Label */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-3 h-3 bg-emerald-500" />
          <span className="text-lg font-retro-body text-emerald-500 uppercase tracking-wider">
            [ SYSTEM DIAGRAM ]
          </span>
        </div>

        {/* Heading Only */}
        <h2 className="font-retro-heading text-xl lg:text-2xl text-white mb-12 leading-relaxed uppercase tracking-wider">
          How It <span className="text-emerald-400">Works</span>
        </h2>

        {/* Architecture Diagram */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          viewport={{ once: true }}
          className="border-2 border-emerald-500/30 overflow-hidden hover:border-emerald-500 transition-colors"
        >
          {isMobile ? (
            <MobileArchitectureView />
          ) : (
            <div className="h-[320px] w-full">
              <ReactFlow
                nodes={architectureNodes}
                edges={architectureEdges}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                proOptions={{ hideAttribution: true }}
                panOnDrag={false}
                zoomOnScroll={false}
                zoomOnPinch={false}
                zoomOnDoubleClick={false}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
                connectionLineType={ConnectionLineType.SmoothStep}
              />
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}
