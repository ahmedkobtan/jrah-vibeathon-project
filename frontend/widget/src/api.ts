export interface ProviderSummary {
  id: number;
  name: string;
  npi?: string | null;
  city?: string | null;
  state?: string | null;
  zip?: string | null;
  phone?: string | null;
  website?: string | null;
}

export interface ProcedureSummary {
  cpt_code: string;
  description: string;
  category?: string | null;
  medicare_rate?: number | null;
}

export interface PriceDetail {
  id: number;
  payer_name?: string | null;
  negotiated_rate?: number | null;
  min_negotiated_rate?: number | null;
  max_negotiated_rate?: number | null;
  standard_charge?: number | null;
  cash_price?: number | null;
  in_network?: boolean | null;
  data_source?: string | null;
  confidence_score?: number | null;
  last_updated?: string | null;
}

export interface PriceEstimateItem {
  provider: ProviderSummary;
  procedure: ProcedureSummary;
  price: PriceDetail;
}

export interface PricingSummary {
  providers_count: number;
  payer_matches: number;
  min_rate?: number | null;
  max_rate?: number | null;
  average_rate?: number | null;
}

export interface PriceEstimateResponse {
  query: {
    cpt_code: string;
    payer_name?: string | null;
    state?: string | null;
    zip?: string | null;
    limit: number;
  };
  summary: PricingSummary;
  results: PriceEstimateItem[];
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? response.statusText);
  }

  return response.json() as Promise<T>;
}

export async function fetchProcedures(
  query?: string,
  limit = 25,
): Promise<ProcedureSummary[]> {
  const url = new URL(`${API_BASE_URL}/procedures`);
  if (query) {
    url.searchParams.set("q", query);
  }
  url.searchParams.set("limit", String(limit));

  const response = await fetch(url);
  return handleResponse<ProcedureSummary[]>(response);
}

export interface PriceEstimateParams {
  cptCode: string;
  payerName?: string;
  state?: string;
  zipCode?: string;
  limit?: number;
}

export async function fetchPriceEstimates(
  params: PriceEstimateParams,
): Promise<PriceEstimateResponse> {
  const url = new URL(`${API_BASE_URL}/pricing/estimates`);
  url.searchParams.set("cpt_code", params.cptCode);
  url.searchParams.set("limit", String(params.limit ?? 20));

  if (params.payerName) {
    url.searchParams.set("payer_name", params.payerName);
  }

  if (params.state) {
    url.searchParams.set("state", params.state.toUpperCase());
  }

  if (params.zipCode) {
    url.searchParams.set("zip_code", params.zipCode);
  }

  const response = await fetch(url);
  return handleResponse<PriceEstimateResponse>(response);
}

