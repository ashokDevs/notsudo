"use client";

interface Step {
  number: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const steps: Step[] = [
  {
    number: "01",
    title: "Tag @notsudo on any issue",
    description: "Found a bug? Need a feature? Just comment @notsudo on any GitHub issue in your repository.",
    icon: (
      <div className="w-16 h-16 border border-orange-500 rounded-sm flex items-center justify-center bg-orange-500/5">
        <span className="text-orange-500 font-mono text-xs font-bold">@ns</span>
      </div>
    ),
  },
  {
    number: "02",
    title: "AI analyzes & codes",
    description: "NotSudo reads the issue, understands your codebase, and writes the fix in an isolated sandbox.",
    icon: (
      <div className="w-16 h-16 border border-gray-600 rounded-sm flex items-center justify-center">
        <div className="font-mono text-[10px] text-gray-400 leading-tight text-center">
          <div className="text-orange-500">▶ run</div>
          <div>████░░</div>
        </div>
      </div>
    ),
  },
  {
    number: "03",
    title: "Review & merge PR",
    description: "Get a clean pull request with tests passing. Review it, request changes, or merge directly.",
    icon: (
      <div className="w-16 h-16 border border-gray-600 rounded-sm flex items-center justify-center relative">
        <div className="w-10 h-8 border border-gray-500 rounded-sm flex items-center justify-center">
          <span className="text-green-500 font-mono text-sm">✓</span>
        </div>
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full" />
      </div>
    ),
  },
];

export function HowItWorksSection() {
  return (
    <section className="relative py-24 px-4 bg-black">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-3 py-1 text-xs font-mono text-gray-400 border border-gray-700 mb-6">
            [ HOW IT WORKS ]
          </span>
          <h2 className="font-mono text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight tracking-tight uppercase">
            FROM ISSUE TO{" "}
            <span className="inline-block border-2 border-orange-500 px-2 py-0.5">
              PR
            </span>
            <br />
            IN 3 STEPS
          </h2>
          <p className="text-gray-500 font-mono text-sm max-w-xl mx-auto mt-4">
            No configuration required. Just install, tag, and ship.
          </p>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-gray-800">
          {steps.map((step, index) => (
            <div
              key={index}
              className="bg-black p-8 relative group hover:bg-gray-900/50 transition-colors"
            >
              {/* Step Number */}
              <div className="absolute top-4 right-4">
                <span className="font-mono text-4xl font-bold text-gray-800 group-hover:text-gray-700 transition-colors">
                  {step.number}
                </span>
              </div>

              {/* Icon */}
              <div className="mb-6">
                {step.icon}
              </div>

              {/* Title */}
              <h3 className="text-lg font-bold text-white mb-3 font-mono">
                {step.title}
              </h3>

              {/* Description */}
              <p className="text-sm text-gray-500 leading-relaxed">
                {step.description}
              </p>

              {/* Connector Line (except last) */}
              {index < steps.length - 1 && (
                <div className="hidden md:block absolute right-0 top-1/2 w-4 h-px bg-gray-700 translate-x-1/2 -translate-y-1/2" />
              )}
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="text-center mt-12">
          <a
            href="/login"
            className="inline-flex items-center gap-2 px-6 py-3 text-xs font-mono text-black bg-white hover:bg-gray-100 transition-all duration-200 border border-white"
          >
            TRY IT NOW — IT'S FREE
          </a>
        </div>
      </div>
    </section>
  );
}
