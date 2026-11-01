"use client";

export default function GlobalError({reset}: {error: Error & {digest?:string}; reset:()=>void}) {
  return <html lang="en" translate="no"><head><title>AEGIS LOOP | Unable to load</title><meta name="google" content="notranslate"/></head><body style={{margin:0,background:"#080f1b",color:"#dce8f7",fontFamily:"Arial, sans-serif"}}><main style={{maxWidth:600,margin:"15vh auto",padding:28}}><p style={{color:"#65e2cf",letterSpacing:3,fontSize:12}}>AEGIS LOOP</p><h1>Unable to load the platform</h1><p style={{lineHeight:1.8,color:"#a9bad0"}}>Retry the page. If the issue continues, open Overview to return to your workspace.</p><div style={{display:"flex",gap:16,alignItems:"center",marginTop:24}}><button onClick={reset} style={{border:0,borderRadius:7,padding:"12px 20px",background:"#65e2cf",color:"#091b20",cursor:"pointer"}}>Retry page</button><a href="/" style={{color:"#a9cfff"}}>Open Overview</a></div></main></body></html>;
}
