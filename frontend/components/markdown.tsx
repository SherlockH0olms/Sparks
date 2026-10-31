import { Fragment } from "react";
// Evidence is rendered as React text. Raw HTML and remote embeds are never interpreted.
export function Markdown({text}:{text:string}){
 const lines=text.split("\n");const blocks:React.ReactNode[]=[];let i=0;
 while(i<lines.length){const line=lines[i];if(!line.trim()){i++;continue;}
 if(line.startsWith("|")&&lines[i+1]?.match(/^\|[- :|]+\|$/)){const split=(s:string)=>s.split("|").slice(1,-1).map(x=>x.trim());const head=split(line);i+=2;const rows:string[][]=[];while(i<lines.length&&lines[i].startsWith("|"))rows.push(split(lines[i++]));blocks.push(<div className="md-table" key={i}><table><thead><tr>{head.map((c,k)=><th key={k}>{c}</th>)}</tr></thead><tbody>{rows.map((r,k)=><tr key={k}>{r.map((c,j)=><td key={j}>{c}</td>)}</tr>)}</tbody></table></div>);continue;}
 const h=line.match(/^(#{1,3}) (.*)/);if(h){blocks.push(h[1].length===1?<h1 key={i}>{h[2]}</h1>:h[1].length===2?<h2 key={i}>{h[2]}</h2>:<h3 key={i}>{h[2]}</h3>);i++;continue;}
 blocks.push(<p key={i}>{line.split(/(\*\*[^*]+\*\*)/).map((p,k)=>p.startsWith("**")?<strong key={k}>{p.slice(2,-2)}</strong>:<Fragment key={k}>{p}</Fragment>)}</p>);i++;
 }return <article className="report-content">{blocks}</article>;
}
