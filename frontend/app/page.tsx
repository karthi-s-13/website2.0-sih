"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getBackendHealth } from "@/lib/api";

type Status = "checking" | "online" | "offline";
const capabilities = [["01", "Early warning", "Surface schedule, cost and delivery signals before they become critical."], ["02", "Evidence-led review", "Bring structured project data, review reports and verified public sources together."], ["03", "Actionable briefings", "Turn complex project information into clear, prioritised next steps."]];

export default function Home() {
  const [status, setStatus] = useState<Status>("checking");
  useEffect(() => { getBackendHealth().then(() => setStatus("online")).catch(() => setStatus("offline")); }, []);
  const statusText = status === "online" ? "Systems operational" : status === "offline" ? "Service temporarily unavailable" : "Verifying service";
  return <>
    <section className="hero"><div className="site-container hero-grid"><div className="hero-copy"><p className="eyebrow"><span /> A unified public infrastructure view</p><h1>See risks early.<br /><em>Deliver public value.</em></h1><p className="hero-text">Nigrani helps programme teams monitor projects with timely, trustworthy intelligence—so attention goes where it is needed most.</p><div className="hero-actions"><Link href="/projects" className="button button-primary">View project dashboard <span aria-hidden="true">→</span></Link><Link href="/analyze" className="button button-secondary">Ask the AI analysis desk</Link></div><div className={`service-status ${status}`} aria-live="polite"><i /> <span>{statusText}</span><small>Live platform status</small></div></div><aside className="hero-panel" aria-label="Platform summary"><div className="panel-top"><span>PORTFOLIO INTELLIGENCE</span><b>Live insight</b></div><div className="map-art" aria-hidden="true"><div className="map-line one"/><div className="map-line two"/><div className="map-line three"/><div className="map-node n1"/><div className="map-node n2"/><div className="map-node n3"/><div className="map-node n4"/></div><div className="panel-rule" /><div className="panel-stat"><strong>One view</strong><span>for project health, risk evidence and recommended actions.</span></div><Link href="/projects" className="panel-link">Explore portfolio <span aria-hidden="true">→</span></Link></aside></div></section>
    <section className="trust-band"><div className="site-container trust-inner"><span>BUILT FOR RESPONSIBLE GOVERNANCE</span><b>Transparent evidence</b><i /><b>Human review in the loop</b><i /><b>Accessible by design</b></div></section>
    <section className="capabilities" id="how-it-works"><div className="site-container"><div className="section-heading"><div><p className="eyebrow dark"><span /> A clearer way to govern delivery</p><h2>From signal to<br />decision, simply.</h2></div><p>Designed to support programme managers, review teams and decision-makers without burying them in complexity.</p></div><div className="capability-grid">{capabilities.map(([number, title, text]) => <article className="capability" key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p><div className="cap-line" /></article>)}</div></div></section>
    <section className="journey"><div className="site-container journey-inner"><div><p className="eyebrow dark"><span /> Start with what matters</p><h2>Make every review<br />count.</h2></div><div className="journey-steps"><div><b>1</b><span>Open the portfolio</span></div><i /><div><b>2</b><span>Understand the risk</span></div><i /><div><b>3</b><span>Act with confidence</span></div></div><Link href="/projects" className="button button-primary">Get started <span aria-hidden="true">→</span></Link></div></section>
  </>;
}
