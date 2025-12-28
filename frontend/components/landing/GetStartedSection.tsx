"use client";

export function GetStartedSection() {
  return (
    <section className="relative bg-black">

      {/* Main Content */}
      <div className="border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-24">
         

          {/* Content */}
          <div className="text-center">

            {/* Title */}
            <h2 className="font-mono text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 tracking-tight uppercase">
              GET STARTED{" "}
              <span className="inline-block border-2 border-white px-2 py-0.5">
                TODAY
              </span>
            </h2>

            {/* Subtitle */}
            <p className="text-gray-400 max-w-lg mx-auto mb-10">
              Stop letting issues pile up. Tag @notsudo and
              <br />
              get working pull requests in minutes, not days.
            </p>

            {/* CTA Button */}
            <div className="flex justify-center">
              <a
                href="/login"
                className="px-8 py-3 text-xs font-mono text-black bg-white hover:bg-gray-100 transition-all duration-200 border border-white"
              >
                START FOR FREE
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

