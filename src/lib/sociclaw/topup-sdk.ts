export type TopupStartRequest = {
  expectedAmountUsd: number;
  chain?: 'base';
  tokenSymbol?: 'USDC';
};

export type TopupStartResponse = {
  success: boolean;
  sessionId: string;
  depositAddress: string;
  amountUsdcExact: string;
  creditsPerUsd: number;
  creditsEstimated: number;
  minDepositUsd: number;
};

export type TopupClaimRequest = {
  sessionId: string;
  txHash: string;
};

export type TopupClaimResponse =
  | {
      success: true;
      status: 'credited';
      sessionId: string;
      creditsCredited: number | null;
    }
  | {
      success?: true;
      status: 'pending' | 'confirming' | 'confirmed';
      sessionId?: string;
      confirmations?: number;
      requiredConfirmations?: number;
      message?: string;
    }
  | {
      error: string;
      message?: string;
      expectedRaw?: string;
      receivedRaw?: string[];
    };

export type TopupStatusResponse = {
  success: true;
  sessionId: string;
  status: 'pending' | 'confirmed' | 'credited' | 'failed' | 'expired';
  amountUsd: number | null;
  creditsEstimated: number | null;
  creditsCredited: number | null;
  txHash: string | null;
  createdAt?: string;
  confirmedAt?: string | null;
  creditedAt?: string | null;
};

export type SociClawTopupClientOptions = {
  baseUrl: string;
  apiKey: string;
  timeoutMs?: number;
  userAgent?: string;
};

export class ApiError extends Error {
  status: number;
  payload: unknown;
  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

const DEFAULT_TIMEOUT_MS = 15_000;

const normalizeBaseUrl = (baseUrl: string) => baseUrl.replace(/\/+$/, '');

async function requestJson<T>(
  options: SociClawTopupClientOptions,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );

  try {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${options.apiKey}`,
      'Content-Type': 'application/json',
    };
    if (options.userAgent) {
      headers['User-Agent'] = options.userAgent;
    }

    const response = await fetch(`${normalizeBaseUrl(options.baseUrl)}${path}`, {
      ...init,
      headers: { ...headers, ...(init?.headers || {}) },
      signal: controller.signal,
    });

    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;

    if (!response.ok) {
      throw new ApiError(
        payload?.error || `HTTP_${response.status}`,
        response.status,
        payload,
      );
    }

    return payload as T;
  } finally {
    clearTimeout(timeout);
  }
}

const toNumberOrNull = (value: unknown): number | null => {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
};

const readNumericField = (
  payload: Record<string, unknown>,
  preferredKey: string,
  fallbackPredicate: (key: string) => boolean,
): number | null => {
  const preferred = toNumberOrNull(payload[preferredKey]);
  if (preferred !== null) return preferred;

  for (const [key, value] of Object.entries(payload)) {
    if (!fallbackPredicate(key)) continue;
    const n = toNumberOrNull(value);
    if (n !== null) return n;
  }
  return null;
};

function normalizeStartTopupResponse(payload: any): TopupStartResponse {
  const bag: Record<string, unknown> = payload && typeof payload === 'object' ? payload : {};
  const creditsPerUsd =
    readNumericField(
      bag,
      'creditsPerUsd',
      (key) => key.toLowerCase().endsWith('perusd') && key.toLowerCase() !== 'amountusdcexact',
    ) ?? 0;
  const creditsEstimated =
    readNumericField(
      bag,
      'creditsEstimated',
      (key) => key.toLowerCase().endsWith('estimated') && key.toLowerCase() !== 'amountusd',
    ) ?? 0;
  return {
    ...payload,
    creditsPerUsd,
    creditsEstimated,
  };
}

function normalizeClaimTopupResponse(payload: any): TopupClaimResponse {
  if (payload?.status !== 'credited') return payload as TopupClaimResponse;
  const bag: Record<string, unknown> = payload && typeof payload === 'object' ? payload : {};
  const creditsCredited = readNumericField(
    bag,
    'creditsCredited',
    (key) => key.toLowerCase().endsWith('credited') && key.toLowerCase() !== 'creditedat',
  );
  return {
    ...payload,
    creditsCredited,
  } as TopupClaimResponse;
}

function normalizeStatusTopupResponse(payload: any): TopupStatusResponse {
  const bag: Record<string, unknown> = payload && typeof payload === 'object' ? payload : {};
  const creditsEstimated = readNumericField(
    bag,
    'creditsEstimated',
    (key) => key.toLowerCase().endsWith('estimated') && key.toLowerCase() !== 'amountusd',
  );
  const creditsCredited = readNumericField(
    bag,
    'creditsCredited',
    (key) => key.toLowerCase().endsWith('credited') && key.toLowerCase() !== 'creditedat',
  );
  return {
    ...payload,
    creditsEstimated,
    creditsCredited,
  };
}

export function createSociClawTopupClient(options: SociClawTopupClientOptions) {
  return {
    startTopup: async (req: TopupStartRequest): Promise<TopupStartResponse> => {
      const payload = await requestJson<any>(options, '/api/v1?path=account/topup/start', {
        method: 'POST',
        body: JSON.stringify({
          expectedAmountUsd: req.expectedAmountUsd,
          chain: req.chain || 'base',
          tokenSymbol: req.tokenSymbol || 'USDC',
        }),
      });
      return normalizeStartTopupResponse(payload);
    },

    claimTopup: async (req: TopupClaimRequest): Promise<TopupClaimResponse> => {
      const payload = await requestJson<any>(options, '/api/v1?path=account/topup/claim', {
        method: 'POST',
        body: JSON.stringify(req),
      });
      return normalizeClaimTopupResponse(payload);
    },

    statusTopup: async (sessionId: string): Promise<TopupStatusResponse> => {
      const payload = await requestJson<any>(
        options,
        `/api/v1?path=account/topup/status&sessionId=${encodeURIComponent(sessionId)}`,
        { method: 'GET' },
      );
      return normalizeStatusTopupResponse(payload);
    },
  };
}

export const startTopup = (options: SociClawTopupClientOptions, req: TopupStartRequest) =>
  createSociClawTopupClient(options).startTopup(req);
export const claimTopup = (options: SociClawTopupClientOptions, req: TopupClaimRequest) =>
  createSociClawTopupClient(options).claimTopup(req);
export const statusTopup = (options: SociClawTopupClientOptions, sessionId: string) =>
  createSociClawTopupClient(options).statusTopup(sessionId);
