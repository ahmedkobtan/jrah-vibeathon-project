import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  PriceEstimateResponse,
  ProcedureSummary,
  ProviderSummary,
  fetchPriceEstimates,
  fetchProcedures,
  smartSearchProcedures,
  lookupProviders,
} from "./api";
import penguinLogo from "./penguin_doctor_logo.png";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

function formatCurrency(value?: number | null): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return currencyFormatter.format(value);
}

function formatConfidence(score?: number | null): string {
  if (score === null || score === undefined) {
    return "n/a";
  }
  return percentFormatter.format(score);
}

export default function App(): JSX.Element {
  const [procedureQuery, setProcedureQuery] = useState("");
  const [procedures, setProcedures] = useState<ProcedureSummary[]>([]);
  const [selectedCpt, setSelectedCpt] = useState("");
  const [payerName, setPayerName] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [zipFilter, setZipFilter] = useState("");
  const [limit, setLimit] = useState(10);

  const [pricing, setPricing] = useState<PriceEstimateResponse | null>(null);
  const [loadingProcedures, setLoadingProcedures] = useState(false);
  const [loadingPricing, setLoadingPricing] = useState(false);
  const [loadingProviderLookup, setLoadingProviderLookup] = useState(false);
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [providerCity, setProviderCity] = useState("Joplin");
  const [providerState, setProviderState] = useState("MO");
  const [providerLimit, setProviderLimit] = useState("20");
  const [error, setError] = useState<string | null>(null);

  // Demo procedures to always show at the top
  const demoProcedures: ProcedureSummary[] = [
    {
      cpt_code: "29881",
      description: "Knee Surgery (Arthroscopy)",
      category: "Orthopedic Surgery",
      medicare_rate: 4500,
    },
    {
      cpt_code: "45378",
      description: "Colonoscopy",
      category: "Gastroenterology",
      medicare_rate: 3200,
    },
  ];

  useEffect(() => {
    const loadProcedures = async () => {
      try {
        setLoadingProcedures(true);
        const data = await fetchProcedures();
        // Put demo procedures first, then merge with API results (removing duplicates)
        const otherProcedures = data.filter(
          (p) => !demoProcedures.find((demo) => demo.cpt_code === p.cpt_code)
        );
        const allProcedures = [...demoProcedures, ...otherProcedures];
        setProcedures(allProcedures);
        if (allProcedures.length > 0) {
          setSelectedCpt((current) => current || allProcedures[0].cpt_code);
        }
      } catch (err) {
        console.error(err);
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load procedure list.",
        );
      } finally {
        setLoadingProcedures(false);
      }
    };

    loadProcedures();
  }, []);

  const handleProcedureSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      setLoadingProcedures(true);
      
      // Use smart search if there's a query (AI-powered)
      if (procedureQuery.trim()) {
        const smartResults = await smartSearchProcedures(procedureQuery, 10);
        
        // Check if any demo procedures match
        const matchingDemos = demoProcedures.filter(
          (demo) =>
            demo.cpt_code.toLowerCase().includes(procedureQuery.toLowerCase()) ||
            demo.description.toLowerCase().includes(procedureQuery.toLowerCase())
        );
        
        // Combine: demo matches first, then AI results (removing duplicates)
        const otherResults = smartResults.filter(
          (p) => !demoProcedures.find((demo) => demo.cpt_code === p.cpt_code)
        );
        const allProcedures = [...matchingDemos, ...otherResults];
        
        setProcedures(allProcedures);
        if (allProcedures.length > 0) {
          setSelectedCpt(allProcedures[0].cpt_code);
        } else {
          // No procedures found - clear selection and show error
          setSelectedCpt("");
          setError(`No procedures found for "${procedureQuery}". Try a different search term like "MRI", "X-ray", or "colonoscopy".`);
        }
      } else {
        // No search query - load all procedures with demos at top
        const data = await fetchProcedures();
        const otherProcedures = data.filter(
          (p) => !demoProcedures.find((demo) => demo.cpt_code === p.cpt_code)
        );
        const allProcedures = [...demoProcedures, ...otherProcedures];
        setProcedures(allProcedures);
        if (allProcedures.length > 0) {
          setSelectedCpt(allProcedures[0].cpt_code);
        }
      }
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error
          ? err.message
          : "There was a problem searching procedures.",
      );
    } finally {
      setLoadingProcedures(false);
    }
  };

  const handleEstimateRequest = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();
    setError(null);
    setPricing(null);

    if (!selectedCpt) {
      setError("Select a procedure to continue.");
      return;
    }

    try {
      setLoadingPricing(true);
      const providerLimitValue = Number(providerLimit) || undefined;
      const response = await fetchPriceEstimates({
        cptCode: selectedCpt,
        payerName: payerName.trim() || undefined,
        state: stateFilter.trim() || undefined,
        zipCode: zipFilter.trim() || undefined,
        limit,
        providerCity: providerCity.trim() || undefined,
        providerState: providerState.trim().toUpperCase() || undefined,
        providerLimit: providerLimitValue,
      });
      setPricing(response);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to fetch price estimates.",
      );
    } finally {
      setLoadingPricing(false);
    }
  };

  const handleProviderLookup = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const city = providerCity.trim();
    const state = providerState.trim().toUpperCase();
    const limitValue = Number(providerLimit);

    if (!city || state.length !== 2) {
      setError("Enter city and two-letter state to search providers.");
      return;
    }

    if (!Number.isInteger(limitValue) || limitValue < 1 || limitValue > 50) {
      setError("Provider limit must be an integer between 1 and 50.");
      return;
    }

    try {
      setLoadingProviderLookup(true);
      const results = await lookupProviders(city, state, limitValue);
      setProviders(results);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to look up providers right now.",
      );
    } finally {
      setLoadingProviderLookup(false);
    }
  };

  const selectedProcedure = useMemo(
    () => procedures.find((proc) => proc.cpt_code === selectedCpt),
    [procedures, selectedCpt],
  );

  return (
    <div className="widget">
      <div className="widget-header">
        <img src={penguinLogo} alt="Penguin Doctor" className="logo" />
        <div>
          <h1>Cost Transparency Explorer</h1>
          <p>
            Compare negotiated rates across providers in seconds. Pick a CPT-coded
            procedure, optionally filter by payer or geography, and explore the
            latest pricing data from the Vibeathon backend.
          </p>
        </div>
      </div>

      <form className="form-grid" onSubmit={handleProcedureSearch}>
        <div className="form-group">
          <label htmlFor="procedure-search">Find a procedure</label>
          <input
            id="procedure-search"
            type="search"
            placeholder="Search by CPT code or description"
            value={procedureQuery}
            onChange={(event) => setProcedureQuery(event.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="procedure-select">Procedure</label>
          <select
            id="procedure-select"
            value={selectedCpt}
            onChange={(event) => setSelectedCpt(event.target.value)}
            disabled={loadingProcedures || procedures.length === 0}
          >
            {procedures.map((procedure) => (
              <option key={procedure.cpt_code} value={procedure.cpt_code}>
                {procedure.cpt_code} · {procedure.description}
              </option>
            ))}
          </select>
        </div>
        <div className="form-actions">
          <button
            type="submit"
            className="primary"
            disabled={loadingProcedures}
          >
            {loadingProcedures ? "Searching…" : "Search Procedures"}
          </button>
        </div>
      </form>

      <form className="form-grid" onSubmit={handleProviderLookup}>
        <div className="form-group">
          <label htmlFor="provider-city">Provider city</label>
          <input
            id="provider-city"
            type="text"
            placeholder="City"
            value={providerCity}
            onChange={(event) => setProviderCity(event.target.value)}
            disabled={!selectedCpt}
          />
        </div>
        <div className="form-group">
          <label htmlFor="provider-state">Provider state</label>
          <input
            id="provider-state"
            type="text"
            placeholder="MO"
            maxLength={2}
            value={providerState}
            onChange={(event) =>
              setProviderState(event.target.value.toUpperCase())
            }
            disabled={!selectedCpt}
          />
        </div>
        <div className="form-group">
          <label htmlFor="provider-limit">Result limit</label>
          <input
            id="provider-limit"
            type="number"
            min={1}
            max={50}
            value={providerLimit}
            onChange={(event) => setProviderLimit(event.target.value)}
            disabled={!selectedCpt}
          />
        </div>
        <div className="form-actions">
          <button
            type="submit"
            className="primary"
            disabled={loadingProviderLookup || !selectedCpt}
            title={!selectedCpt ? "Please search and select a procedure first" : ""}
          >
            {loadingProviderLookup ? "Looking up…" : "Lookup Providers"}
          </button>
        </div>
      </form>

      <form className="form-grid" onSubmit={handleEstimateRequest}>
        <div className="form-group">
          <label htmlFor="payer-name">Payer (optional)</label>
          <input
            id="payer-name"
            type="text"
            placeholder="Blue Cross, Medicare, United…"
            value={payerName}
            onChange={(event) => setPayerName(event.target.value)}
            disabled={!selectedCpt}
          />
        </div>
        <div className="form-group">
          <label htmlFor="state">State (optional)</label>
          <input
            id="state"
            type="text"
            placeholder="MO"
            maxLength={2}
            value={stateFilter}
            onChange={(event) => setStateFilter(event.target.value)}
            disabled={!selectedCpt}
          />
        </div>
        <div className="form-group">
          <label htmlFor="zip">ZIP (optional)</label>
          <input
            id="zip"
            type="text"
            placeholder="64801"
            value={zipFilter}
            onChange={(event) => setZipFilter(event.target.value)}
            disabled={!selectedCpt}
          />
        </div>
        <div className="form-group">
          <label htmlFor="limit">Result limit</label>
          <input
            id="limit"
            type="number"
            min={1}
            max={50}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
            disabled={!selectedCpt}
          />
        </div>
        <div className="form-actions">
          <button 
            type="submit" 
            className="primary" 
            disabled={loadingPricing || !selectedCpt}
            title={!selectedCpt ? "Please search and select a procedure first" : ""}
          >
            {loadingPricing ? "Fetching…" : "Get Estimates"}
          </button>
        </div>
      </form>

      {selectedProcedure && (
        <div className="results">
          <h2>
            {selectedProcedure.cpt_code} · {selectedProcedure.description}
          </h2>
          {selectedProcedure.medicare_rate ? (
            <p>
              Medicare baseline:{" "}
              <strong>
                {formatCurrency(selectedProcedure.medicare_rate)}
              </strong>
            </p>
          ) : null}
        </div>
      )}

      {error && <div className="error">{error}</div>}
      {loadingPricing && (
        <div className="loading">Crunching negotiated rate data…</div>
      )}

      {pricing && pricing.results.length > 0 && (
        <section className="results">
          {selectedProcedure && (
            <div className="info-banner" style={{ 
              backgroundColor: selectedProcedure.category === "Web Search Result" ? "#fff3cd" : "#d1ecf1",
              padding: "1rem",
              marginBottom: "1rem",
              borderRadius: "4px",
              border: selectedProcedure.category === "Web Search Result" ? "1px solid #ffc107" : "1px solid #bee5eb"
            }}>
              <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.1rem" }}>
                📋 Showing Prices For: <strong>{selectedProcedure.cpt_code}</strong> - {selectedProcedure.description}
              </h3>
              {selectedProcedure.category === "Web Search Result" && (
                <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.9rem", color: "#856404" }}>
                  ⚡ This procedure was found via web search since it's not in our local database
                </p>
              )}
              {selectedProcedure.medicare_rate && (
                <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.9rem" }}>
                  Medicare baseline: <strong>{formatCurrency(selectedProcedure.medicare_rate)}</strong>
                </p>
              )}
            </div>
          )}
          <div className="summary">
            <div className="summary-item">
              <span>Providers matched</span>
              <span className="summary-highlight">
                {pricing.summary.providers_count}
              </span>
            </div>
            <div className="summary-item">
              <span>Negotiated rate range</span>
              <span className="summary-highlight">
                {formatCurrency(pricing.summary.min_rate)} –{" "}
                {formatCurrency(pricing.summary.max_rate)}
              </span>
            </div>
            <div className="summary-item">
              <span>Average negotiated rate</span>
              <span className="summary-highlight">
                {formatCurrency(pricing.summary.average_rate)}
              </span>
            </div>
            <div className="summary-item">
              <span>Records returned</span>
              <span className="summary-highlight">
                {pricing.summary.payer_matches}
              </span>
            </div>
          </div>

          {pricing.summary.payer_matches === 0 && (
            <div className="info-banner">
              Negotiated rates were unavailable, so we’re showing estimated
              market prices for nearby providers based on public benchmarks.
            </div>
          )}

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Payer</th>
                  <th>Negotiated Rate</th>
                  <th>Standard Charge</th>
                  <th>Cash Price</th>
                  <th>Confidence</th>
                  <th>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {pricing.results.map((result) => (
                  <tr key={result.price.id}>
                    <td>
                      <strong>{result.provider.name}</strong>
                      <div>
                        {[result.provider.city, result.provider.state]
                          .filter(Boolean)
                          .join(", ")}
                      </div>
                    </td>
                    <td>{result.price.payer_name ?? "—"}</td>
                    <td>{formatCurrency(result.price.negotiated_rate)}</td>
                    <td>{formatCurrency(result.price.standard_charge)}</td>
                    <td>{formatCurrency(result.price.cash_price)}</td>
                    <td>{formatConfidence(result.price.confidence_score)}</td>
                    <td>
                      {result.price.last_updated
                        ? new Date(result.price.last_updated).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {providers.length > 0 && (
        <section className="results">
          <h2>Providers Found</h2>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>NPI</th>
                  <th>Location</th>
                  <th>Phone</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((provider) => (
                  <tr key={`${provider.npi ?? provider.name}`}>
                    <td>{provider.name}</td>
                    <td>{provider.npi ?? "—"}</td>
                    <td>
                      {[provider.city, provider.state, provider.zip]
                        .filter(Boolean)
                        .join(", ")}
                    </td>
                    <td>{provider.phone ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {pricing && pricing.results.length === 0 && !loadingPricing && (
        <div className="error">
          No negotiated rates found for this combination yet. Try broadening
          your filters or removing payer/state criteria.
        </div>
      )}
    </div>
  );
}
