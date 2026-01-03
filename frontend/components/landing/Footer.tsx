"use client";

export function Footer() {
  return (
    <footer className="py-12 px-4 bg-black border-t-2 border-orange-500/30">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex gap-6 text-lg text-gray-500 font-retro-body uppercase tracking-wider">
          <a href="#" className="hover:text-orange-500 transition-colors">[ Terms ]</a>
          <a href="#" className="hover:text-orange-500 transition-colors">[ Privacy ]</a>
        </div>

        <div className="text-lg text-gray-600 font-retro-body uppercase tracking-wider">
          © {new Date().getFullYear()} NotSudo
        </div>
      </div>
    </footer>
  );
}

