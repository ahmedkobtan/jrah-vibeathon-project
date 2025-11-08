export type QueryParseResponse = {
  procedure: string;
  cpt_code: string;
  insurance: string;
  location: string;
  confidence: number;
};

export type ServiceEstimate = {
  cpt_code: string;
  negotiated_rate: number;
  patient_responsibility?: number;
};

export type FacilityEstimate = {
  facility: string;
  distance_miles?: number;
  services: ServiceEstimate[];
  source?: string;
  confidence?: number;
  coverage_percent?: number;
};

export type EstimateResponse = {
  results: Record<string, FacilityEstimate[]>;
};

const API_BASE = import.meta.env.VITE_TRANSPARENTCARE_API_BASE ?? 'http://localhost:8000';

export async function fetchParseQuery(query: string): Promise<QueryParseResponse> {
  const response = await fetch(`${API_BASE}/parse-query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  if (!response.ok) {
    throw new Error(`parse-query failed: ${response.status}`);
  }
  return response.json();
}

export type EstimateParams = {
  cpt_code: string;
  insurance: string;
  zip: string;
  radius?: number;
  include_out_of_network?: boolean;
};

export async function fetchEstimate(params: EstimateParams): Promise<EstimateResponse> {
  const query = new URLSearchParams({
    cpt_code: params.cpt_code,
    insurance: params.insurance,
    zip: params.zip,
    radius: String(params.radius ?? 50),
    include_out_of_network: String(params.include_out_of_network ?? true)
  });
  const response = await fetch(`${API_BASE}/estimate?${query.toString()}`);
  if (!response.ok) {
    throw new Error(`estimate failed: ${response.status}`);
  }
  return response.json();
}
