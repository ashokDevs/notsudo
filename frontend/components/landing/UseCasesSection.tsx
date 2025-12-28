"use client";

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
}

const features: Feature[] = [
  {
    icon: (
      <div className="w-16 h-16 border border-orange-500 rounded-sm flex items-center justify-center bg-orange-500/5">
        <div className="text-orange-500 font-mono text-lg">🐛</div>
      </div>
    ),
    title: "Bug Fixes on Autopilot",
    description: "Assign bug issues to your AI junior dev and wake up to working PRs. No more debugging at 2 AM.",
  },
  {
    icon: (
      <div className="w-16 h-16 border border-gray-600 rounded-sm flex flex-col items-center justify-center p-1.5">
        <div className="text-gray-400 font-mono text-[8px] leading-tight">
          <div>+ feature</div>
          <div>+ tests</div>
          <div>+ docs</div>
        </div>
      </div>
    ),
    title: "Feature Development",
    description: "Describe what you need in the issue, and watch your junior dev implement it with proper tests.",
  },
  {
    icon: (
      <div className="w-16 h-16 border border-gray-600 rounded-sm flex items-center justify-center">
        <div className="font-mono text-[8px] text-gray-400 leading-tight">
          <div>━━━━━━</div>
          <div>━━ → ━━</div>
          <div>━━━━━━</div>
        </div>
      </div>
    ),
    title: "Code Refactoring",
    description: "Point at messy code, get clean, documented, and tested refactors. Tech debt? What tech debt?",
  },
  {
    icon: (
      <div className="w-16 h-16 border border-gray-600 rounded-sm flex items-center justify-center relative">
        <div className="w-10 h-8 border border-gray-500 rounded-sm flex items-center justify-center">
          <span className="text-orange-500 font-mono text-sm">PR</span>
        </div>
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full flex items-center justify-center">
          <span className="text-[6px] text-white">✓</span>
        </div>
      </div>
    ),
    title: "PR-Ready Code",
    description: "Every change comes as a clean PR with descriptions, proper commits, and passing CI checks.",
  },
  {
    icon: (
      <div className="w-16 h-16 border border-gray-600 rounded-sm flex items-center justify-center">
        <div className="font-mono text-[10px] text-green-500 leading-tight">
          <div>✓ test 1</div>
          <div>✓ test 2</div>
          <div>✓ test 3</div>
        </div>
      </div>
    ),
    title: "Test Generation",
    description: "Automatically generates unit tests and integration tests. Finally, that 80% coverage goal is achievable.",
  },
  {
    icon: (
      <div className="w-16 h-16 border border-orange-500 rounded-sm flex items-center justify-center bg-orange-500/5">
        <div className="text-orange-500 font-mono text-[9px] leading-tight text-center">
          <div>NO PTO</div>
          <div>NO 1:1s</div>
          <div>24/7 🚀</div>
        </div>
      </div>
    ),
    title: "Zero HR Issues",
    description: "No 1-on-1s, no standups, no vacation requests. Just pure, uninterrupted shipping. Every. Single. Day.",
  },
];

export function UseCasesSection() {
  return (
    <section className="relative py-24 px-4 bg-black">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-3 py-1 text-xs font-mono text-gray-400 border border-gray-700 mb-6">
            [ FEATURES ]
          </span>
          <h2 className="font-mono text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight tracking-tight uppercase">
            SUPERCHARGE YOUR{" "}
            <span className="inline-block border-2 border-orange-500 px-2 py-0.5">
              WORKFLOW
            </span>
          </h2>
          <p className="text-gray-500 font-mono text-sm max-w-xl mx-auto mt-4">
            Everything a junior developer does, but faster, cheaper, and without the coffee breaks.
          </p>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-gray-800">
          {features.map((feature, index) => (
            <div
              key={index}
              className="bg-black p-8 flex flex-col items-center text-center group hover:bg-gray-900/50 transition-colors"
            >
              {/* Icon */}
              <div className="mb-6">
                {feature.icon}
              </div>

              {/* Title */}
              <h3 className="text-base font-bold text-white mb-3 font-mono">
                {feature.title}
              </h3>

              {/* Description */}
              <p className="text-sm text-gray-500 max-w-xs leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
