import { useState } from 'react';

import { SearchForm } from './components/SearchForm';
import { ResultList } from './components/ResultList';
import { StructuredForm, type StructuredValues } from './components/StructuredForm';
import {
  EstimateResponse,
  fetchEstimate,
  fetchParseQuery,
  type QueryParseResponse
} from './services/apiClient';

const defaultStructuredValues: StructuredValues = {
  cpt_code: '',
  insurance: '',
  zip: '',
  radius: 50,
  include_out_of_network: true
};

export function WidgetApp() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [parseResult, setParseResult] = useState<QueryParseResponse | null>(null);
  const [structuredValues, setStructuredValues] = useState<StructuredValues>(defaultStructuredValues);
  const [results, setResults] = useState<EstimateResponse | null>(null);

  const requestEstimates = async (values: StructuredValues) => {
    const estimates = await fetchEstimate({
      cpt_code: values.cpt_code,
      insurance: values.insurance,
      zip: values.zip,
      radius: values.radius,
      include_out_of_network: values.include_out_of_network
    });
    setResults(estimates);
  };

  const handleSearch = async ({ query }: { query: string }) => {
    setLoading(true);
    setError(null);
    setNotice(null);
    setResults(null);

    try {
      const parsed = await fetchParseQuery(query);
      setParseResult(parsed);
      const merged: StructuredValues = {
        ...structuredValues,
        cpt_code: parsed.cpt_code || structuredValues.cpt_code,
        insurance: parsed.insurance || structuredValues.insurance,
        zip: parsed.location || structuredValues.zip
      };
      setStructuredValues(merged);
      const hasAll = Boolean(merged.cpt_code && merged.insurance && merged.zip);
      if (hasAll) {
        await requestEstimates(merged);
      } else {
        setNotice('Review the structured fields below and fill in any missing details.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleStructuredChange = (values: StructuredValues) => {
    setStructuredValues(values);
  };

  const handleStructuredSubmit = async (values: StructuredValues) => {
    setStructuredValues(values);
    setLoading(true);
    setError(null);
    setNotice(null);
    setResults(null);
    try {
      await requestEstimates(values);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tc-widget">
      <SearchForm loading={loading} onSubmit={handleSearch} />
      {parseResult ? <ParseSummary parse={parseResult} /> : null}
      {notice ? <p className="tc-notice">{notice}</p> : null}
      {error ? <p className="tc-error">{error}</p> : null}
      <StructuredForm
        values={structuredValues}
        disabled={loading}
        onChange={handleStructuredChange}
        onSubmit={handleStructuredSubmit}
      />
      <ResultList data={results ?? undefined} />
    </div>
  );
}

type ParseSummaryProps = {
  parse: QueryParseResponse;
};

function ParseSummary({ parse }: ParseSummaryProps) {
  return (
    <div className="tc-parse-summary">
      <span>Procedure: {parse.procedure || 'unknown'}</span>
      <span>CPT: {parse.cpt_code || 'n/a'}</span>
      <span>Insurance: {parse.insurance || 'n/a'}</span>
      <span>Location: {parse.location || 'n/a'}</span>
      <span>Confidence: {(parse.confidence * 100).toFixed(0)}%</span>
    </div>
  );
}
