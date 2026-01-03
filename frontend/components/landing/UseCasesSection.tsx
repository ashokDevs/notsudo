"use client";

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
}

const features: Feature[] = [
  {
    icon: (
      <div className="w-16 h-16 border-2 border-green-500 flex items-center justify-center bg-green-500/10">
        <div className="text-green-500 font-retro-body text-2xl">🐛</div>
      </div>
    ),
    title: "Bug Fixes on Autopilot",
    description: "Assign bug issues to your AI junior dev and wake up to working PRs. No more debugging at 2 AM.",
  },
  {
    icon: (
      <div className="w-16 h-16 border-2 border-cyan-500 flex flex-col items-center justify-center p-1.5">
        <div className="text-cyan-400 font-retro-body text-sm leading-tight">
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
      <div className="w-16 h-16 border-2 border-purple-500 flex items-center justify-center">
        <div className="font-retro-body text-sm text-purple-400 leading-tight">
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
      <div className="w-16 h-16 border-2 border-orange-500 flex items-center justify-center relative">
        <div className="w-10 h-8 border-2 border-orange-400 flex items-center justify-center">
          <span className="text-orange-500 font-retro-body text-lg">PR</span>
        </div>
        <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 flex items-center justify-center">
          <span className="text-xs text-black font-bold">✓</span>
        </div>
      </div>
    ),
    title: "PR-Ready Code",
    description: "Every change comes as a clean PR with descriptions, proper commits, and passing CI checks.",
  },
  {
    icon: (
      <div className="w-16 h-16 border-2 border-green-500 flex items-center justify-center">
        <div className="font-retro-body text-base text-green-500 leading-tight">
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
      <div className="w-16 h-16 border-2 border-pink-500 flex items-center justify-center bg-pink-500/10">
        <div className="text-pink-500 font-retro-body text-sm leading-tight text-center">
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
    <section className="relative py-24 px-4 bg-black border-t-2 border-orange-500/30">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-2 text-lg font-retro-body text-orange-500 border-2 border-orange-500/50 mb-6 uppercase tracking-wider">
            [ FEATURES ]
          </span>
          <h2 className="font-retro-heading text-xl md:text-2xl lg:text-3xl text-white mb-4 leading-relaxed tracking-wide uppercase">
            SUPERCHARGE YOUR{" "}
            <span className="inline-block border-4 border-orange-500 px-4 py-2 retro-box-glow">
              WORKFLOW
            </span>
          </h2>
          <p className="text-gray-500 font-retro-body text-xl max-w-xl mx-auto mt-6">
            Everything a junior developer does, but faster, cheaper, and without the coffee breaks.
          </p>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-1 bg-orange-500/20">
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
              <h3 className="text-lg font-retro-body text-white mb-3 uppercase tracking-wider">
                {feature.title}
              </h3>

              {/* Description */}
              <p className="text-base font-retro-body text-gray-500 max-w-xs leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

