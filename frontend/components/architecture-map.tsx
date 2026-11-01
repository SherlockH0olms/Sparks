"use client";

import Link from "next/link";
import { useId, useState, type CSSProperties } from "react";
import type { Health } from "@/lib/api";
import { Icon } from "./platform";
import "./architecture-map.css";

type RoleId = "red" | "control" | "target" | "judge";
const colors: Record<RoleId, string> = { red: "#ec8d97", control: "#ad98f6", target: "#80b7fa", judge: "#85cbb5" };
const roles: { id: RoleId; number: string; title: string; label: string; icon: string; description: string; read: string; write: string; link: string; action: string }[] = [
  { id: "red", number: "01", title: "Offensive intelligence", label: "Red model", icon: "activity", description: "Builds and adapts attacks using recorded framework sources, executable transformations and the target’s declared attack surfaces.", read: "Scoped manifest + public responses", write: "User messages + assigned documents", link: "/campaign", action: "Explore attack activity" },
  { id: "control", number: "02", title: "Security control plane", label: "AEGIS Loop", icon: "layers", description: "Connects the model roles to one versioned experiment. Scope, permissions, resource accounting and execution records stay attached to the target snapshot.", read: "Target snapshot + declared scope", write: "Campaign checkpoints + evidence", link: "/audit", action: "Inspect access and audit" },
  { id: "target", number: "03", title: "Application under test", label: "Target application", icon: "target", description: "Runs the registered model API behind the application adapter. Responses, retrieved documents and simulated tool effects become observable evidence.", read: "Task policy + retrieved context", write: "Responses + simulated tool effects", link: "/target", action: "View the target registry" },
  { id: "judge", number: "04", title: "Independent evaluation", label: "Judge + boundary checks", icon: "check", description: "Evaluates recorded behavior against the declared security rules. Server-owned checks and semantic evaluation support fresh-session reproduction and independent defense verification.", read: "Observed behavior + protected oracle", write: "Assessments + verification results", link: "/verification", action: "Open independent verification" },
];

function Orbit({ x, y, color, prefix, selected = false }: { x: number; y: number; color: string; prefix: string; selected?: boolean }) {
  const points = [[-48,-20],[-20,-42],[38,-31],[60,6],[28,37],[-32,34],[-61,8]];
  return <g transform={`translate(${x} ${y})`}>
    <circle r="79" fill={selected ? color + "0b" : "#131820"} stroke={color} strokeOpacity={selected ? .45 : .13}/>
    <g fill="none" stroke={selected ? color : "#697581"} strokeWidth=".85" opacity={selected ? .74 : .48}>
      <ellipse rx="68" ry="25"/><ellipse rx="67" ry="25" transform="rotate(62)"/><ellipse rx="67" ry="25" transform="rotate(-62)"/>
    </g>
    {points.map(([px,py],i)=><circle key={i} cx={px} cy={py} r={i===3?6:4.5} fill={i%2===0?color:`url(#${prefix}-dark-sphere)`} stroke={color} strokeOpacity=".3"/>)}
    <circle r="17" fill={`url(#${prefix}-sphere-${color.slice(1)})`} stroke={color} strokeOpacity=".7"/>
    <path d="m-8 0 8-8 8 8-8 8-8-8Zm8-8v16M-8 0H8" stroke="#f0effa" strokeWidth=".7" fill="none" opacity=".8"/>
  </g>;
}

function RecordNode({ x, y, title, subtitle, color = "#ad98f6", icon = "file" }: { x:number;y:number;title:string;subtitle:string;color?:string;icon?:string }) {
  return <g transform={`translate(${x} ${y})`}>
    <path d="M-65-20 54-20 64-10 64 28-55 28-65 18Z" fill="#171e28" stroke="#465364" strokeWidth=".8"/>
    <path d="M-65-20-55-10H64M-55-10V28" fill="none" stroke="#465364" strokeWidth=".6"/>
    <rect x="-45" y="-2" width="15" height="17" rx="1" fill={color+"12"} stroke={color} strokeWidth=".8"/>
    {icon==="shield"?<path d="m-42 2 4-2 5 2v5c0 3-5 5-5 5s-4-2-4-5V2Z" fill="none" stroke={color} strokeWidth=".6"/>:<path d="M-42 3h8m-8 4h8m-8 4h5" stroke={color} strokeWidth=".6"/>}
    <text x="-21" y="4" fill="#e4e8ef" fontSize="10.8">{title}</text><text x="-21" y="17" fill="#8492a3" fontSize="8.4">{subtitle}</text>
    <circle cx="56" cy="-14" r="2.1" fill={color}/>
  </g>;
}

function ArchitectureScene({ selected, prefix }: { selected: RoleId; prefix: string }) {
  return <svg className="architecture-scene" viewBox="0 0 1100 545" role="img" aria-labelledby={`${prefix}-title ${prefix}-description`}>
    <title id={`${prefix}-title`}>AEGIS model roles, trust boundaries and evidence loop</title>
    <desc id={`${prefix}-description`}>Red reads a scoped manifest and writes attacks through AEGIS to the target. Public target responses can feed attack adaptation. Independent evaluation reads the recorded observations and protected oracle. Findings, controls and verification results connect to the evidence chain.</desc>
    <defs>
      <pattern id={`${prefix}-grid`} width="26" height="26" patternUnits="userSpaceOnUse"><path d="M26 0H0V26" fill="none" stroke="#34404d" strokeWidth=".5"/></pattern>
      {Object.values(colors).map(color=><radialGradient key={color} id={`${prefix}-sphere-${color.slice(1)}`} cx="32%" cy="20%"><stop stopColor="#e8eaf4"/><stop offset=".48" stopColor={color}/><stop offset="1" stopColor="#263140"/></radialGradient>)}
      <radialGradient id={`${prefix}-dark-sphere`} cx="25%" cy="20%"><stop stopColor="#69737d"/><stop offset=".5" stopColor="#27313a"/><stop offset="1" stopColor="#11171c"/></radialGradient>
      <linearGradient id={`${prefix}-floor`} x2="1" y2="1"><stop stopColor="#232a36"/><stop offset="1" stopColor="#121a24"/></linearGradient>
      {Object.entries(colors).map(([id,color])=><marker key={id} id={`${prefix}-arrow-${id}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="m1 1 7 4-7 4" fill="none" stroke={color} strokeWidth="1.5"/></marker>)}
      <clipPath id={`${prefix}-board`}><path d="M360 190 740 190 892 330 208 330Z"/></clipPath>
    </defs>

    <g className="architecture-plane">
      <path d="M360 205 740 205 892 345H208Z" fill="#0c121a" stroke="#3a4758"/>
      <path d="M208 330v15h684v-15M360 190v15m380-15v15" stroke="#384455" fill="none" strokeWidth=".7"/>
      <path d="M360 190 740 190 892 330H208Z" fill={`url(#${prefix}-floor)`} stroke="#576173" strokeWidth=".9"/>
      <g clipPath={`url(#${prefix}-board)`} opacity=".4" transform="matrix(1 0 -.78 .6 255 145)"><rect width="800" height="500" fill={`url(#${prefix}-grid)`}/></g>
      <path d="M424 237 550 206 704 257 735 310 494 314 378 272 424 237Z" stroke="#a38ada" strokeWidth="1" strokeOpacity=".55" fill="#9a79db08"/>
      <path d="M400 256h115q20 0 20 20v23h91q20 0 20-20v-50h103" stroke="#a995f7" strokeWidth="1.2" fill="none"/>
      <path d="M453 293 550 239 658 283M494 314 583 270 714 309" stroke="#607489" strokeWidth=".8" fill="none"/>
      <RecordNode x={411} y={242} title="Attack" subtitle="SCOPED INPUT" color={colors.red}/>
      <RecordNode x={552} y={204} title="Target snapshot" subtitle="VERSIONED CONTEXT" color={colors.control}/>
      <RecordNode x={736} y={248} title="Observation" subtitle="RESPONSE + EFFECTS" color={colors.target}/>
      <RecordNode x={625} y={300} title="Assessment" subtitle="BOUNDARY + EVIDENCE" color={colors.judge}/>
      <RecordNode x={411} y={306} title="Control variant" subtitle="ISOLATED CONFIGURATION" color={colors.control} icon="shield"/>
      <text x="552" y="366" textAnchor="middle" fill="#e2d8fc" fontSize="12" letterSpacing="2">VERSIONED SECURITY MODEL</text>
      <text x="552" y="383" textAnchor="middle" fill="#75859a" fontSize="10">scope · policy · observations · controls</text>
    </g>

    <g className={`architecture-route route-red ${selected==="red"||selected==="control"?"is-emphasized":""}`} fill="none" stroke={colors.red}>
      <path d="M245 172h52q20 0 20 20v43h40" strokeWidth="1.2" markerEnd={`url(#${prefix}-arrow-red)`}/>
      <path d="M468 242h8q21 0 21-23v-58q0-21 22-21h300" strokeWidth="1.1" markerEnd={`url(#${prefix}-arrow-red)`}/>
      <text x="621" y="130" stroke="none" fill={colors.red} fontSize="10" letterSpacing="1.2">WRITE / TEST INPUT</text>
    </g>
    <g className={`architecture-route route-target ${selected==="target"||selected==="red"?"is-emphasized":""}`} fill="none" stroke={colors.target}>
      <path d="M913 179v53q0 17-18 17h-95" strokeWidth="1.1" markerEnd={`url(#${prefix}-arrow-target)`}/>
      <path className="architecture-flow" d="M855 99V74q0-15-18-15H241q-18 0-18 15v17" strokeWidth="1" strokeDasharray="4 5" markerEnd={`url(#${prefix}-arrow-target)`}/>
      <text x="552" y="48" textAnchor="middle" stroke="none" fill="#92aecd" fontSize="10" letterSpacing="1.5">READ / PUBLIC RESPONSE FEEDBACK</text>
    </g>
    <g className={`architecture-route route-judge ${selected==="judge"||selected==="target"?"is-emphasized":""}`} fill="none" stroke={colors.judge}>
      <path d="M795 267h105q20 0 20 20v39" strokeWidth="1.1" markerEnd={`url(#${prefix}-arrow-judge)`}/>
      <path d="M847 378h-88q-20 0-20-20v-35h-58" strokeWidth="1.1" markerEnd={`url(#${prefix}-arrow-judge)`}/>
      <path d="M907 455v-18" strokeWidth="1.1" markerEnd={`url(#${prefix}-arrow-judge)`}/>
      <text x="810" y="289" stroke="none" fill={colors.judge} fontSize="9.5">READ / OBSERVATIONS</text>
    </g>

    <Orbit x={185} y={166} color={colors.red} prefix={prefix} selected={selected==="red"}/>
    <Orbit x={914} y={157} color={colors.target} prefix={prefix} selected={selected==="target"}/>
    <Orbit x={922} y={375} color={colors.judge} prefix={prefix} selected={selected==="judge"}/>
    <g transform="translate(551 118)">
      <path d="m0-45 41 22v43L0 42-41 20v-43L0-45Z" fill="#1e2133" stroke={colors.control} strokeOpacity={selected==="control"?.9:.5}/>
      <path d="M-41-23 0 0l41-23M0 0v42M0-45v45M-41 20 0 0l41 20" fill="none" stroke={colors.control} strokeOpacity=".5"/>
      <path d="m0-21 16 9v15c0 12-16 21-16 21S-16 15-16 3v-15L0-21Z" fill="#171a28" stroke="#d2c4fc" strokeWidth="1"/>
      <path d="m-7 2 5 5 10-13" fill="none" stroke="#d2c4fc" strokeWidth="1.3"/>
    </g>

    <g fill="#e5eaf1" fontSize="15">
      <text x="185" y="270" textAnchor="middle">Red model</text>
      <text x="551" y="178" textAnchor="middle" fontSize="13">AEGIS Loop</text>
      <text x="914" y="266" textAnchor="middle">Target application</text>
      <text x="922" y="480" textAnchor="middle">Independent evaluation</text>
    </g>
    <g fill="#7e8ea3" fontSize="9.5" letterSpacing="1.1">
      <text x="185" y="287" textAnchor="middle">ATTACK GENERATION + ADAPTATION</text>
      <text x="922" y="497" textAnchor="middle">JUDGE + DETERMINISTIC ORACLES</text>
    </g>

    <g transform="translate(77 345)">
      <path d="M0 0h184v109H0Z" fill="#131b25" stroke="#334052" strokeWidth=".8"/>
      <path d="M0 24h184" stroke="#334052" strokeWidth=".8"/>
      <text x="12" y="16" fill="#a6b6cc" fontSize="9" letterSpacing="1.5">RED ACCESS PROFILE</text>
      {["Scoped target manifest","Assigned documents","Public observations"].map((t,i)=><g key={t}><circle cx="14" cy={42+i*24} r="2.5" fill={colors.target}/><text x="25" y={45+i*24} fill="#b5c1d0" fontSize="10.5">{t}</text></g>)}
      <path d="M91 0v-35" stroke="#678dab" strokeDasharray="3 4" markerEnd={`url(#${prefix}-arrow-target)`}/>
    </g>
    <g transform="translate(773 516)">
      <rect x="0" y="0" width="290" height="23" fill="#85cbb505" stroke="#527e70" strokeOpacity=".5"/>
      <path d="M11 8V5a3 3 0 0 1 6 0v3m-7 0h8v9h-8V8Z" fill="none" stroke={colors.judge} strokeWidth=".8"/>
      <text x="27" y="15" fill="#96b8ac" fontSize="9" letterSpacing=".7">EVALUATOR ONLY / PROTECTED ORACLE</text>
      <path d="M270 0v-96h-53" stroke={colors.judge} strokeDasharray="3 4" markerEnd={`url(#${prefix}-arrow-judge)`}/>
    </g>

    <g transform="translate(315 424)">
      <text x="0" y="0" fill="#aab7c8" fontSize="9" letterSpacing="2">EVIDENCE / APPEND THE RECORD</text>
      <path d="M2 27h340" stroke="#486359" strokeWidth=".8"/>
      {["Input","Observation","Finding","Control","Verification","Report"].map((t,i)=><g key={t} transform={`translate(${i*63} 21)`}>
        <rect x="0" y="0" width="17" height="18" fill="#19212a" stroke={i>1?colors.judge:"#77869a"} strokeWidth=".8"/>
        <path d="M4 5h9m-9 4h9m-9 4h6" stroke={i>1?colors.judge:"#77869a"} strokeWidth=".65"/>
        <text x="8" y="34" textAnchor="middle" fill="#a9b6c7" fontSize="8.5">{t}</text>
      </g>)}
      <text x="0" y="88" fill="#748498" fontSize="9">reproduce → isolate controls → verify independently → report</text>
    </g>
  </svg>;
}

export function ArchitectureMap({ health, targetCount, campaignId }: { health: Health | null; targetCount: number; campaignId?: string }) {
  const [selected,setSelected] = useState<RoleId>("control");
  const prefix = "aegis-architecture-" + useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const role = roles.find(r=>r.id===selected)!;
  const model = (id:RoleId) => id==="red" ? health?.red.model || "Not configured" : id==="judge" ? health?.fixture_environment ? "Server-owned fixture checks" : health?.judge.model || "Not configured" : id==="target" ? `${targetCount} registered target${targetCount===1?"":"s"}` : "Access · Scope · Evidence";
  const ready = (id:RoleId) => id==="red" ? health?.red.configured : id==="judge" ? health?.judge.configured || health?.fixture_environment : id==="target" ? targetCount>0 : health?.status==="ok";
  const status = (id:RoleId) => ready(id) ? id==="target" ? "Targets registered" : id==="control" ? "API connected" : id==="judge"&&health?.fixture_environment ? "Fixture evaluation" : "Configured" : "Setup required";
  const href = role.link + (campaignId ? "?campaign="+encodeURIComponent(campaignId) : "");
  const library = health?.red_attack_library;
  return <section className="architecture-map" aria-label="Security architecture" data-selected-role={selected}>
    <header className="architecture-header">
      <div><span className="architecture-kicker">AEGIS / SYSTEM ARCHITECTURE</span><h2>Anatomy of a security experiment.</h2><p>Four roles. Explicit trust boundaries. One evidence trail.</p></div>
      <div className="architecture-health"><span className={health?.status==="ok"?"architecture-online":""}/>{health?.status==="ok"?"Control plane online":health?"Control plane unavailable":"Checking connection"}<small>{health?.workers.active_jobs ?? 0} active campaigns</small></div>
    </header>
    <div className="architecture-role-nav" aria-label="Explore the model roles">
      {roles.map(r=><button key={r.id} type="button" className={"architecture-role "+(selected===r.id?"is-selected":"")} aria-pressed={selected===r.id} aria-controls={`${prefix}-inspector`} onClick={()=>setSelected(r.id)} style={{"--role-color":colors[r.id]} as CSSProperties}>
        <div className="architecture-role-rule"><span>{r.number}</span><span>{r.title}</span><Icon name="arrow" size={14}/></div>
        <strong>{r.label}</strong><span className="architecture-model">{model(r.id)}</span>
        <span className={"architecture-role-status "+(ready(r.id)?"is-ready":"")}><i/>{status(r.id)}</span>
      </button>)}
    </div>
    <div className="architecture-drawing"><ArchitectureScene selected={selected} prefix={prefix}/><div className="architecture-mobile-mark"><OrbitMobile color={colors[selected]}/><span>{role.number} / {role.title}</span><strong>{role.label}</strong><p>Attack → Observe → Reproduce → Verify</p></div></div>
    <div id={`${prefix}-inspector`} className="architecture-inspector" style={{"--role-color":colors[selected]} as React.CSSProperties} aria-live="polite">
      <div className="architecture-inspector-title"><span className="architecture-inspector-icon"><Icon name={role.icon} size={22}/></span><div><span className="architecture-kicker">SELECTED ROLE / {role.number}</span><h3>{role.label}</h3></div></div>
      <div className="architecture-inspector-body"><p>{role.description}</p><div className="architecture-permissions"><span><b>READ</b>{role.read}</span><span><b>WRITE</b>{role.write}</span></div></div>
      <Link href={href} className="architecture-detail-link">{role.action}<Icon name="arrow" size={16}/></Link>
    </div>
    <footer className="architecture-footer"><span><i style={{background:colors.target}}/>DATA / {library?.unique_resources?.toLocaleString("en-US") ?? "—"} library resources</span><span><i style={{background:colors.control}}/>LOGIC / {library?.mechanism_groups ?? "—"} attack mechanisms</span><span><i style={{background:colors.judge}}/>ACTION / Reproduce · Verify · Report</span></footer>
  </section>;
}

function OrbitMobile({color}:{color:string}) {
  return <svg viewBox="0 0 320 230" aria-hidden="true"><g transform="translate(160 115)" fill="none" stroke={color} strokeWidth=".8"><circle r="91" strokeOpacity=".2" fill={color+"05"}/><ellipse rx="83" ry="32"/><ellipse rx="83" ry="32" transform="rotate(60)"/><ellipse rx="83" ry="32" transform="rotate(-60)"/><path d="m0-29 25 14v29L0 29-25-15v-14L0-29Z" fill="#191d2b"/><path d="M-25-15 0 0l25-15M0 0v29"/>{[[-71,-16],[-31,53],[70,18],[37,-49]].map(([x,y],i)=><circle key={i} cx={x} cy={y} r="6" fill={color}/>)}</g></svg>;
}
