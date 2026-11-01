import type { Campaign, CampaignRow, Target } from "./api";

export const targetName = (target: Target) => target.display_name ?? target.name;
export const targetOption = (target: Target) => `${targetName(target)} · ${target.model}${target.is_latest_for_model ? " · Latest" : ""}`;
export const campaignName = (campaign: Campaign | CampaignRow) => campaign.display_name ?? "Security test";
export const campaignOption = (campaign: CampaignRow) => `${campaignName(campaign)}${campaign.target_name ? " · " + campaign.target_name : ""}`;
