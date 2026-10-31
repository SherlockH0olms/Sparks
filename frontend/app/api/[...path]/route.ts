import { NextRequest } from "next/server";
import fs from "node:fs";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function backendUrl() {
  if (process.env.AEGIS_API) return process.env.AEGIS_API.replace(/\/$/, "");
  const envPath = path.resolve(process.cwd(), "..", ".env");
  const value = fs.existsSync(envPath)
    ? fs.readFileSync(envPath, "utf8").split(/\r?\n/).find(line => line.startsWith("AEGIS_API="))?.slice(10).trim().replace(/^["']|["']$/g, "")
    : undefined;
  return value || "http://127.0.0.1:8000";
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const params = await context.params;
  const headers = new Headers(request.headers);
  for (const name of ["host", "connection", "content-length", "transfer-encoding"]) headers.delete(name);
  try {
    const upstream = await fetch(backendUrl() + "/api/" + params.path.map(encodeURIComponent).join("/") + request.nextUrl.search, {
      method: request.method, headers, cache: "no-store", redirect: "manual", signal: request.signal,
      body: request.method === "GET" ? undefined : await request.arrayBuffer(),
    });
    const responseHeaders = new Headers(upstream.headers);
    for (const name of ["connection", "transfer-encoding", "content-encoding", "content-length"]) responseHeaders.delete(name);
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return Response.json({ detail: "Platform API bağlantısı kurulamadı. Backend sunucusunu kontrol edin." }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
