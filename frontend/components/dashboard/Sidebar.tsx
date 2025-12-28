"use client";

import { usePathname } from "next/navigation";
import { Briefcase, Settings, User, Coins } from "lucide-react";

const navItems = [
  { name: "Jobs", href: "/dashboard", icon: Briefcase },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  // Hardcoded user data for now
  const user = {
    name: "John Doe",
    credits: 0,
  };

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-black border-r border-white/10 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-white/10">
        <a href="/" className="flex items-center gap-2">
          <img src="/logo.png" alt="NotSudo" className="w-8 h-8" />
          <span className="font-mono font-bold text-white text-lg">NotSudo</span>
        </a>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.name}>
                <a
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg font-mono text-sm transition-all ${
                    isActive
                      ? "bg-orange-500/10 text-orange-500 border border-orange-500/20"
                      : "text-gray-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User Profile - Footer */}
      <div className="px-4 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-2">
          <div className="w-10 h-10 rounded-full bg-orange-500/20 border border-orange-500/30 flex items-center justify-center">
            <User className="w-5 h-5 text-orange-500" />
          </div>
          <div>
            <p className="font-mono text-sm text-white">{user.name}</p>
            <div className="flex items-center gap-1 text-gray-500">
              <Coins className="w-3 h-3" />
              <span className="font-mono text-xs">{user.credits} credits</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

