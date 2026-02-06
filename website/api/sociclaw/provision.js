// Vercel Serverless Function (Node)
//
// Purpose:
// - Keep OPENCLAW_PROVISION_SECRET on the server (Vercel env var)
// - Proxy provisioning requests to your upstream image account provider
//
// Security:
// - This endpoint can be abused to mass-provision accounts if left public.
// - If you set SOCICLAW_INTERNAL_TOKEN, the function will require:
//   Authorization: Bearer <SOCICLAW_INTERNAL_TOKEN>

const UPSTREAM_URL = process.env.SOCICLAW_PROVISION_UPSTREAM_URL;

function sendJson(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

async function readJson(req) {
  let raw = "";
  for await (const chunk of req) raw += chunk;
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return sendJson(res, 405, { error: "Method Not Allowed" });
  }

  const internalToken = process.env.SOCICLAW_INTERNAL_TOKEN;
  if (internalToken) {
    const auth = req.headers["authorization"] || "";
    const expected = `Bearer ${internalToken}`;
    if (auth !== expected) return sendJson(res, 401, { error: "Unauthorized" });
  }

  const openclawSecret = process.env.OPENCLAW_PROVISION_SECRET;
  if (!openclawSecret) return sendJson(res, 500, { error: "Missing OPENCLAW_PROVISION_SECRET" });
  if (!UPSTREAM_URL) return sendJson(res, 500, { error: "Missing SOCICLAW_PROVISION_UPSTREAM_URL" });

  const body = await readJson(req);
  if (body === null) return sendJson(res, 400, { error: "Invalid JSON body" });

  const provider = body.provider;
  const provider_user_id = body.provider_user_id;
  const create_api_key = body.create_api_key !== false;

  if (!provider || !provider_user_id) {
    return sendJson(res, 400, { error: "Missing required fields: provider, provider_user_id" });
  }

  const payload = {
    provider: String(provider),
    provider_user_id: String(provider_user_id),
    create_api_key: Boolean(create_api_key),
  };

  let upstreamResp;
  try {
    upstreamResp = await fetch(UPSTREAM_URL, {
      method: "POST",
      headers: {
        "x-openclaw-secret": openclawSecret,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    return sendJson(res, 502, { error: "Upstream request failed", detail: String(err) });
  }

  const text = await upstreamResp.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = { raw: text };
  }

  // Pass through upstream status + body (never returns the provisioning secret)
  return sendJson(res, upstreamResp.status, data);
}
