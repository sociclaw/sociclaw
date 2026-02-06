// Vercel Serverless Function (Node)
//
// Purpose:
// - Keep OPENCLAW_PROVISION_SECRET on the server (Vercel env var)
// - Proxy provisioning requests to your upstream image account provider
//
// Security:
// - If SOCICLAW_INTERNAL_TOKEN is set, require:
//   Authorization: Bearer <SOCICLAW_INTERNAL_TOKEN>

const UPSTREAM_URL = process.env.SOCICLAW_PROVISION_UPSTREAM_URL;
const PROVIDER_PATTERN = /^[a-z0-9_-]{2,32}$/i;
const PROVIDER_USER_ID_PATTERN = /^[a-zA-Z0-9:_@.\-]{1,128}$/;
const RATE_LIMIT_DISABLED = process.env.SOCICLAW_RATE_LIMIT_DISABLED === "true";
const RATE_LIMIT_WINDOW_SECONDS = Number(process.env.SOCICLAW_RATE_LIMIT_WINDOW_SECONDS || 3600);
const RATE_LIMIT_MAX_PER_IP = Number(process.env.SOCICLAW_RATE_LIMIT_MAX_PER_IP || 20);
const RATE_LIMIT_MAX_PER_USER = Number(process.env.SOCICLAW_RATE_LIMIT_MAX_PER_USER || 5);
const RATE_LIMIT_STORE_KEY = "__sociclawProvisionRateLimitStore";
const MAX_RATE_LIMIT_KEYS = Number(process.env.SOCICLAW_RATE_LIMIT_MAX_KEYS || 5000);

function sendJson(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
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

function getRateStore() {
  if (!globalThis[RATE_LIMIT_STORE_KEY]) {
    globalThis[RATE_LIMIT_STORE_KEY] = new Map();
  }
  return globalThis[RATE_LIMIT_STORE_KEY];
}

function pruneRateStore(store, nowMs) {
  if (store.size <= MAX_RATE_LIMIT_KEYS) return;
  for (const [k, v] of store.entries()) {
    if (!v || !v.resetAt || v.resetAt <= nowMs) {
      store.delete(k);
    }
    if (store.size <= MAX_RATE_LIMIT_KEYS) break;
  }
}

function applyRateLimit({ bucketKey, limit, windowSeconds, nowMs }) {
  if (RATE_LIMIT_DISABLED) {
    return { allowed: true, remaining: Number.MAX_SAFE_INTEGER, retryAfterSeconds: 0 };
  }
  const safeLimit = Number.isFinite(limit) && limit > 0 ? Math.floor(limit) : 1;
  const safeWindow = Number.isFinite(windowSeconds) && windowSeconds > 0 ? Math.floor(windowSeconds) : 60;
  const windowMs = safeWindow * 1000;
  const store = getRateStore();
  pruneRateStore(store, nowMs);

  let rec = store.get(bucketKey);
  if (!rec || rec.resetAt <= nowMs) {
    rec = { count: 0, resetAt: nowMs + windowMs };
  }

  if (rec.count >= safeLimit) {
    const retryAfterSeconds = Math.max(1, Math.ceil((rec.resetAt - nowMs) / 1000));
    return {
      allowed: false,
      remaining: 0,
      retryAfterSeconds,
    };
  }

  rec.count += 1;
  store.set(bucketKey, rec);
  return {
    allowed: true,
    remaining: Math.max(0, safeLimit - rec.count),
    retryAfterSeconds: 0,
  };
}

function getClientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (typeof fwd === "string" && fwd.trim()) {
    return fwd.split(",")[0].trim();
  }
  const realIp = req.headers["x-real-ip"];
  if (typeof realIp === "string" && realIp.trim()) {
    return realIp.trim();
  }
  return req.socket?.remoteAddress || "unknown";
}

export default async function handler(req, res) {
  // Minimal CORS for browser-based diagnostics.
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  if (req.method === "OPTIONS") {
    res.statusCode = 204;
    return res.end();
  }

  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return sendJson(res, 405, { error: "Method Not Allowed" });
  }

  const nowMs = Date.now();
  const clientIp = getClientIp(req);
  const ipRate = applyRateLimit({
    bucketKey: `ip:${clientIp}`,
    limit: RATE_LIMIT_MAX_PER_IP,
    windowSeconds: RATE_LIMIT_WINDOW_SECONDS,
    nowMs,
  });
  if (!ipRate.allowed) {
    res.setHeader("Retry-After", String(ipRate.retryAfterSeconds));
    return sendJson(res, 429, {
      error: "Rate limit exceeded for IP",
      retry_after_seconds: ipRate.retryAfterSeconds,
    });
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

  const providerNormalized = String(provider).trim();
  const providerUserIdNormalized = String(provider_user_id).trim();
  if (!PROVIDER_PATTERN.test(providerNormalized)) {
    return sendJson(res, 400, { error: "Invalid provider format" });
  }
  if (!PROVIDER_USER_ID_PATTERN.test(providerUserIdNormalized)) {
    return sendJson(res, 400, { error: "Invalid provider_user_id format" });
  }

  const userRate = applyRateLimit({
    bucketKey: `user:${providerNormalized}:${providerUserIdNormalized}`,
    limit: RATE_LIMIT_MAX_PER_USER,
    windowSeconds: RATE_LIMIT_WINDOW_SECONDS,
    nowMs,
  });
  if (!userRate.allowed) {
    res.setHeader("Retry-After", String(userRate.retryAfterSeconds));
    return sendJson(res, 429, {
      error: "Rate limit exceeded for provider_user_id",
      retry_after_seconds: userRate.retryAfterSeconds,
    });
  }

  const payload = {
    provider: providerNormalized,
    provider_user_id: providerUserIdNormalized,
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
