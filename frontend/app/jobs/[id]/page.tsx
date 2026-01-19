"use client";

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, FileCode, Clock, Terminal, MessageSquare, Cpu, Zap, Shield, Loader2, CheckCircle2, AlertCircle, User, ExternalLink, ChevronDown, Trash2, Settings } from 'lucide-react';
import ReactDiffViewer from 'react-diff-viewer-continued';
import { cn } from '@/lib/utils';
import { useSession } from '@/lib/auth-client';
import { getSocket } from '@/lib/socket';

interface JobLogEntry {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  type: 'message' | 'command' | 'file_change' | 'error' | 'info' | 'screenshot';
  content: string;
  metadata?: any;
  createdAt: string;
}

interface FileChange {
  path: string;
  content: string;
  reason: string;
  timestamp: string;
}

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const { data: session } = useSession();
  
  const [logs, setLogs] = useState<JobLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [fileChanges, setFileChanges] = useState<FileChange[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchLogs = async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}/feed`);
        if (!res.ok) throw new Error('Failed to fetch logs');
        const data = await res.json();
        
        if (isMounted) {
          setLogs(data.entries || []);
          
          const changes: FileChange[] = [];
          const seenPaths = new Set();
          
          [...(data.entries || [])].reverse().forEach((log: JobLogEntry) => {
             if ((log.type === 'file_change' || log.metadata?.file_path) && log.metadata?.new_content) {
               const path = log.metadata.file_path;
               if (!seenPaths.has(path)) {
                 changes.push({
                   path,
                   content: log.metadata.new_content,
                   reason: log.content,
                   timestamp: log.createdAt
                 });
                 seenPaths.add(path);
               }
             }
          });
          
          setFileChanges(changes);
          if (!selectedFile && changes.length > 0) {
            setSelectedFile(changes[0].path);
          }
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchLogs();

    // Setup Socket.IO
    const socket = getSocket();
    
    socket.emit('join_job', { jobId });

    socket.on('job_log', (data: { jobId: string; entry: JobLogEntry }) => {
      if (data.jobId === jobId) {
        setLogs(prev => {
          // Prevent duplicates
          if (prev.some(l => l.id === data.entry.id)) return prev;
          return [...prev, data.entry];
        });

        // Update file changes if it's a file_change
        const log = data.entry;
        if ((log.type === 'file_change' || log.metadata?.file_path) && log.metadata?.new_content) {
          const path = log.metadata.file_path;
          setFileChanges(prev => {
            const index = prev.findIndex(f => f.path === path);
            const newChange = {
              path,
              content: log.metadata.new_content,
              reason: log.content,
              timestamp: log.createdAt
            };
            
            if (index !== -1) {
              const updated = [...prev];
              updated[index] = newChange;
              return updated;
            } else {
              if (!selectedFile) setSelectedFile(path);
              return [...prev, newChange];
            }
          });
        }
      }
    });

    socket.on('job_status', (data: { jobId: string; status: string; stage?: string }) => {
      if (data.jobId === jobId) {
        // We might want to update some local state for status/stage here if we had it
        // For now, it's just reflected in logs, but we could add status state if needed.
        console.log('Job status updated:', data);
      }
    });
    
    return () => {
      isMounted = false;
      socket.emit('leave_job', { jobId });
      socket.off('job_log');
      socket.off('job_status');
    };
  }, [jobId, selectedFile]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const selectedFileContent = fileChanges.find(f => f.path === selectedFile)?.content || '';

  return (
    <div className="flex h-screen bg-[#020202] text-zinc-100 overflow-hidden font-modern selection:bg-orange-500/30">
      <main className="flex-1 flex flex-col h-screen relative">
        {/* Modern Top Nav */}
        <header className="h-16 border-b border-zinc-800/50 flex items-center justify-between px-6 bg-black/20 backdrop-blur-xl sticky top-0 z-50">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="flex items-center gap-2 group">
               <div className="w-6 h-6 bg-orange-600 rounded-md flex items-center justify-center transform group-hover:rotate-12 transition-transform shadow-lg shadow-orange-500/20">
                 <span className="text-white text-[10px] font-bold">N</span>
               </div>
               <span className="font-bold text-lg tracking-tight">notsudo</span>
            </Link>
            <div className="h-4 w-[1px] bg-zinc-800 mx-2" />
            <div className="flex items-center gap-2 px-3 py-1 bg-orange-500/5 border border-orange-500/10 rounded-full">
              <div className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse" />
              <span className="text-[10px] font-bold text-orange-400 uppercase tracking-widest">Live Stream</span>
            </div>
            <span className="text-zinc-500 text-xs font-medium uppercase tracking-widest">Job #{jobId.split('-')[1] || jobId.substring(0,8)}</span>
          </div>

          <div className="flex items-center gap-4">
             <div className="flex items-center gap-2 bg-emerald-500/10 px-3 py-1.5 border border-emerald-500/20 rounded-lg">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-emerald-500 uppercase">Streaming live</span>
             </div>
             
             <div className="w-px h-6 bg-zinc-800 mx-2" />

             {session?.user && (
               <div className="w-8 h-8 rounded-full border border-zinc-800 overflow-hidden bg-zinc-900 flex items-center justify-center">
                 {session.user.image ? (
                   <img src={session.user.image} alt="User" className="w-full h-full object-cover" />
                 ) : (
                   <User className="w-4 h-4 text-zinc-600" />
                 )}
               </div>
             )}
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          {/* File Changes Panel */}
          <div className="w-1/2 flex flex-col border-r border-zinc-800/50 bg-zinc-900/10">
            <div className="p-4 border-b border-zinc-800/50 flex items-center justify-between bg-zinc-900/20">
              <div className="flex items-center gap-3">
                <FileCode className="w-4 h-4 text-zinc-500" />
                <span className="text-sm font-semibold text-zinc-400 uppercase tracking-tight">Modified files ({fileChanges.length})</span>
              </div>
            </div>
            
            <div className="flex-1 flex flex-col overflow-hidden relative">
               {fileChanges.length === 0 ? (
                 <div className="flex-1 flex flex-col items-center justify-center p-12 gap-4">
                    <Loader2 className="w-6 h-6 text-zinc-800 animate-spin" />
                    <span className="text-xs text-zinc-700 font-medium uppercase tracking-widest">Awaiting payload</span>
                 </div>
               ) : (
                 <>
                   <div className="flex overflow-x-auto bg-zinc-900/30 scrollbar-hide border-b border-zinc-800/50">
                     {fileChanges.map(file => (
                       <button
                         key={file.path}
                         onClick={() => setSelectedFile(file.path)}
                         className={cn(
                           "px-6 py-3 text-xs font-semibold whitespace-nowrap transition-all relative",
                           selectedFile === file.path 
                             ? "text-white bg-zinc-900/50" 
                             : "text-zinc-600 hover:text-zinc-400"
                         )}
                       >
                         {file.path.split('/').pop()}
                         {selectedFile === file.path && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-600 rounded-full" />
                         )}
                       </button>
                     ))}
                   </div>
                   
                   <div className="flex-1 overflow-auto bg-[#0a0a0a] relative group border-t border-zinc-800/20">
                     <ReactDiffViewer 
                       oldValue="" 
                       newValue={selectedFileContent} 
                       splitView={true}
                       useDarkTheme={true}
                       styles={{
                         variables: {
                           dark: {
                             diffViewerBackground: 'transparent',
                             diffViewerColor: '#a1a1aa',
                             addedBackground: 'rgba(16, 185, 129, 0.05)',
                             addedColor: '#10b981',
                             wordAddedBackground: 'rgba(16, 185, 129, 0.1)',
                             removedBackground: 'rgba(239, 68, 68, 0.05)',
                             removedColor: '#ef4444',
                             wordRemovedBackground: 'rgba(239, 68, 68, 0.1)',
                             gutterBackground: 'transparent',
                             gutterColor: '#3f3f46',
                           }
                         },
                         line: {
                            fontFamily: 'var(--font-modern), Menlo, monospace',
                            fontSize: '13px',
                         }
                       }}
                     />
                   </div>
                 </>
               )}
            </div>
          </div>

          {/* Activity Feed Panel */}
          <div className="w-1/2 flex flex-col bg-zinc-900/5">
            <div className="p-4 border-b border-zinc-800/50 flex items-center justify-between bg-zinc-900/20">
              <div className="flex items-center gap-3">
                <Terminal className="w-4 h-4 text-zinc-500" />
                <span className="text-sm font-semibold text-zinc-400 uppercase tracking-tight">Activity log</span>
              </div>
              <Zap className="w-4 h-4 text-zinc-800" />
            </div>

            <div className="flex-1 overflow-y-auto p-8 space-y-8 modern-scrollbar">
              {logs.length === 0 && loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-4">
                  <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                  <span className="text-sm text-zinc-600 font-medium uppercase tracking-widest">Connecting to frequency...</span>
                </div>
              ) : logs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                   <Terminal className="w-10 h-10 text-zinc-800" />
                   <div className="space-y-1">
                      <p className="text-zinc-500 font-bold uppercase tracking-widest">No activity data</p>
                      <p className="text-[10px] text-zinc-700 font-medium">Ready for transmission</p>
                   </div>
                </div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="group relative">
                    <div className="flex items-start gap-4">
                      <div className="flex-none pt-1">
                        <div className={cn(
                          "w-8 h-8 rounded-lg flex items-center justify-center border transition-all",
                          log.role === 'user' ? "bg-zinc-900 border-zinc-800 text-zinc-500" : "bg-orange-600/10 border-orange-500/20 text-orange-500"
                        )}>
                          {log.type === 'command' ? <Terminal className="w-4 h-4" /> : 
                           log.type === 'file_change' ? <FileCode className="w-4 h-4" /> : 
                           log.type === 'error' ? <AlertCircle className="w-4 h-4" /> :
                           log.role === 'user' ? <User className="w-4 h-4" /> :
                           <Cpu className="w-4 h-4" />}
                        </div>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-2 pb-1 border-b border-zinc-800/20">
                          <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-wider">
                            {log.role === 'assistant' ? 'AI Agent' : log.role.toUpperCase()}
                          </span>
                          <span className="text-[10px] text-zinc-700 font-medium">{new Date(log.createdAt).toLocaleTimeString()}</span>
                        </div>

                        {log.type === 'file_change' ? (
                          <div className="bg-orange-500/5 border border-orange-500/10 rounded-xl p-4 group-hover:border-orange-500/30 transition-all">
                             <div className="flex items-center gap-3 mb-2">
                                <FileCode className="w-4 h-4 text-orange-500" />
                                <span className="text-sm font-bold text-orange-400 truncate">{log.metadata?.file_path}</span>
                             </div>
                             <p className="text-xs text-zinc-400 mb-4 line-clamp-2">{log.content}</p>
                             <button 
                                onClick={() => {
                                   if (log.metadata?.file_path) {
                                      setSelectedFile(log.metadata.file_path);
                                   }
                                }}
                                className="flex items-center gap-2 text-[10px] font-bold text-orange-500 hover:text-orange-400 uppercase tracking-widest transition-colors"
                             >
                                View diff <ArrowLeft className="w-3 h-3 rotate-180" />
                             </button>
                             <div className="text-zinc-500 mt-3 font-mono text-[9px] uppercase flex items-center gap-2">
                                <span className="px-1.5 py-0.5 bg-orange-500/10 text-orange-500 rounded border border-orange-500/20">Job #{jobId.slice(0, 8)}</span>
                                <span>•</span>
                                <span>{log.metadata?.repo || 'codebase'}</span>
                             </div>
                          </div>
                        ) : log.type === 'command' ? (
                          <div className="font-mono text-xs text-orange-400 bg-orange-600/5 border border-orange-500/10 rounded-lg px-4 py-3">
                             <span className="text-orange-900 mr-2">$</span> {log.content}
                          </div>
                        ) : log.type === 'screenshot' ? (
                          <div className="mt-2 rounded-xl overflow-hidden border border-zinc-800 bg-black/40">
                             <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 bg-zinc-900/50">
                                <span className="text-[10px] font-mono text-zinc-500 truncate max-w-[200px]">{log.metadata?.url}</span>
                                <a href={log.content} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[10px] font-bold text-orange-500 hover:text-orange-400 uppercase tracking-wider">
                                   Full Size <ExternalLink className="w-3 h-3" />
                                </a>
                             </div>
                             <div className="relative aspect-video bg-zinc-900/20">
                                <img
                                  src={log.content}
                                  alt="Screenshot"
                                  className="absolute inset-0 w-full h-full object-contain"
                                />
                             </div>
                          </div>
                        ) : (
                          <div className={cn(
                            "text-sm leading-relaxed whitespace-pre-wrap font-medium",
                            log.type === 'error' ? "text-red-400" : "text-zinc-400"
                          )}>
                            {log.content}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
