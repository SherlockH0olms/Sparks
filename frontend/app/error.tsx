"use client";
import Link from "next/link";
import {Button, Panel} from "@/components/platform";

export default function PageError({reset}: {error: Error & {digest?:string}; reset:()=>void}) {
  return <Panel><section role="alert"><h1>Unable to load this page</h1><p className="small gap-top">Retry the page, or return to Overview to open another part of your workspace.</p><div className="row wrap gap-top"><Button variant="primary" onClick={reset}>Retry page</Button><Link className="button" href="/">Open Overview</Link></div></section></Panel>;
}
