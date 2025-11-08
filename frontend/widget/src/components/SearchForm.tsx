import { FormEvent, useState } from 'react';

export type SearchFormValues = {
  query: string;
};

type Props = {
  defaultQuery?: string;
  loading?: boolean;
  onSubmit: (values: SearchFormValues) => void;
};

export function SearchForm({ defaultQuery = '', loading = false, onSubmit }: Props) {
  const [query, setQuery] = useState(defaultQuery);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit({ query });
  };

  return (
    <form className="tc-form" onSubmit={handleSubmit}>
      <label className="tc-label">
        Ask about a procedure cost
        <input
          className="tc-input"
          type="text"
          placeholder="How much for knee MRI with Blue Cross near 64801?"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={loading}
        />
      </label>
      <button className="tc-button" type="submit" disabled={loading || !query.trim()}>
        {loading ? 'Searching…' : 'Search'}
      </button>
    </form>
  );
}
