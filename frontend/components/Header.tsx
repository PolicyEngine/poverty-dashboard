import Image from "next/image";

export function Header() {
  return (
    <header className="border-b border-primary-900 bg-primary-900 text-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <a
          href="https://policyengine.org"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3"
        >
          <Image
            src="/assets/logos/policyengine-white.svg"
            alt="PolicyEngine"
            width={140}
            height={29}
            priority
          />
        </a>

        <nav className="flex items-center gap-4 text-sm">
          <a
            href="https://github.com/PolicyEngine/poverty-dashboard"
            target="_blank"
            rel="noreferrer"
            className="text-primary-100 hover:text-white"
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}

export function PageHeader() {
  return (
    <div className="border-b border-secondary-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight text-secondary-900">
          Baseline poverty dashboard
        </h1>
      </div>
    </div>
  );
}
