"use client";
import { RedDiversity } from "@/lib/api";
import { Panel } from "./platform";

export function RedDiversityView({ value }: { value?: RedDiversity }) {
  if (!value) return null;
  return <Panel title="Attack diversity observed">
    <div className="row wrap">
      <span>{value.distinct_methods} distinct methods</span>
      <span>· {value.distinct_resources} source examples</span>
      {value.distinct_tactics_composed != null && <span>· {value.distinct_tactics_composed} tactics used in composition ({value.tactic_compositions ?? 0} compositions)</span>}
      <span>· {value.applied_transformations} applied transformations</span>
      <span>· {value.frameworks_used.join(" / ") || "No source or transformation usage yet"}</span>
    </div>
    <p className="small muted">{value.generated_candidates} candidates measured from recorded tool activity. {value.unattributed_candidates > 0 && `${value.unattributed_candidates} candidates have no recorded method. `}Method counts describe generated tests. Attack success is measured separately on the target.</p>
  </Panel>;
}
