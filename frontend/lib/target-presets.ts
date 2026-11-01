import { TargetConnection, TargetSpec } from "./api";

// Ephemeral public-tunnel example (ngrok tunnels expire; replace with the
// current endpoint when reproducing the Granite live validation run).
export const GRANITE_URL = "https://8e79-136-118-38-222.ngrok-free.app/v1";
export function granitePreset(template: TargetSpec, endpoint: string): TargetSpec & TargetConnection {
  const url = endpoint.trim().replace(/\/$/, "");
  return {...template, name:"GRANIT-4-test-2", endpoint:url.endsWith("/v1") ? url : url + "/v1",
    model:"granite-4.2-8b", model_revision:"granite-4.2-8b-Q4_K_M.gguf", application_revision:"aegis-local-app-v2",
    connection_kind:"ngrok", api_format:"openai_compatible", tool_mode:"json", max_output_tokens:null, timeout_seconds:null,
    api_key:"", access_client_id:"", access_client_secret:""};
}
