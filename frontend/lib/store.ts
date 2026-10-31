"use client";

import { useEffect, useState } from "react";

/** Aktif kampanya kimliğini tarayıcı yerel deposunda tutar. */
export function useActiveCampaign() {
  const [campaignId, setCampaignId] = useState<string | null>(null);
  useEffect(() => {
    const saved = typeof window !== "undefined" ? window.localStorage.getItem("aegis.campaign") : null;
    setCampaignId(saved);
  }, []);
  const set = (id: string | null) => {
    setCampaignId(id);
    if (typeof window !== "undefined") {
      if (id) window.localStorage.setItem("aegis.campaign", id);
      else window.localStorage.removeItem("aegis.campaign");
    }
  };
  return [campaignId, set] as const;
}
