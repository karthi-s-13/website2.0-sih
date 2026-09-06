import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { ARIAProvider } from "./components/ARIAContext";
import ARIAChat from "./components/ARIAChat";

export const metadata: Metadata = {
  title: "Nigrani | National Project Monitoring",
  description: "An AI-enabled early-warning platform for public infrastructure projects.",
};

function Emblem() {
  return (
    <div className="emblem" aria-hidden="true">
      <span /><span /><span />
    </div>
  );
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ARIAProvider>
          <a className="skip-link" href="#main-content">Skip to main content</a>

          {/* Gov Strip */}
          <div className="gov-strip">
            <div className="site-container gov-strip-inner">
              <span>भारत सरकार <span aria-hidden="true">|</span> Government of India</span>
              <div className="gov-tools">
                <button type="button">A−</button>
                <button type="button">A</button>
                <button type="button">A+</button>
                <span aria-hidden="true">|</span>
                <button type="button">हिंदी</button>
              </div>
            </div>
          </div>

          {/* Site Header */}
          <header className="site-header">
            <div className="site-container brand-row">
              <Link href="/" className="brand" aria-label="Nigrani home">
                <Emblem />
                <span>
                  <strong>NIGRANI</strong>
                  <small>National Infrastructure Governance &amp; Risk Analytics Network Interface</small>
                </span>
              </Link>
              <div className="ministry-mark">
                AI-ENABLED PUBLIC SERVICE<br />
                <b>Project Monitoring Platform</b>
              </div>
            </div>
            <nav className="primary-nav" aria-label="Primary navigation">
              <div className="site-container nav-inner">
                <Link href="/">Overview</Link>
                <Link href="/projects">Project dashboard</Link>
                <Link href="/analyze">AI analysis desk</Link>
                <a href="/#how-it-works">How it works</a>
                <span className="nav-spacer" />
                <Link className="nav-cta" href="/projects">
                  Open dashboard <span aria-hidden="true">→</span>
                </Link>
              </div>
            </nav>
          </header>

          {/* Page Content */}
          <main id="main-content">{children}</main>

          {/* Footer */}
          <footer className="site-footer">
            <div className="site-container footer-inner">
              <span>© Government of India · Nigrani Project Monitoring Platform</span>
              <span>Designed for transparency, timely action and accountable delivery.</span>
            </div>
          </footer>

          {/* ARIA — persistent AI chat assistant */}
          <ARIAChat />
        </ARIAProvider>
      </body>
    </html>
  );
}
