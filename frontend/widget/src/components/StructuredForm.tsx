import { FormEvent } from 'react';

export type StructuredValues = {
  cpt_code: string;
  insurance: string;
  zip: string;
  radius: number;
  include_out_of_network: boolean;
};

type Props = {
  values: StructuredValues;
  disabled?: boolean;
  onChange: (values: StructuredValues) => void;
  onSubmit: (values: StructuredValues) => void;
};

export function StructuredForm({ values, disabled = false, onChange, onSubmit }: Props) {
  const handleFieldChange = (field: keyof StructuredValues, value: string | boolean) => {
    onChange({ ...values, [field]: value });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(values);
  };

  return (
    <form className="tc-structured" onSubmit={handleSubmit}>
      <div className="tc-structured-grid">
        <label>
          CPT Code
          <input
            type="text"
            value={values.cpt_code}
            onChange={(event) => handleFieldChange('cpt_code', event.target.value)}
            placeholder="73721"
            disabled={disabled}
          />
        </label>
        <label>
          Insurance
          <input
            type="text"
            value={values.insurance}
            onChange={(event) => handleFieldChange('insurance', event.target.value)}
            placeholder="Blue Cross"
            disabled={disabled}
          />
        </label>
        <label>
          ZIP / State
          <input
            type="text"
            value={values.zip}
            onChange={(event) => handleFieldChange('zip', event.target.value)}
            placeholder="64801"
            disabled={disabled}
          />
        </label>
        <label>
          Radius (mi)
          <input
            type="number"
            min={5}
            max={250}
            step={5}
            value={values.radius}
            onChange={(event) => handleFieldChange('radius', Number(event.target.value))}
            disabled={disabled}
          />
        </label>
        <label className="tc-checkbox">
          <input
            type="checkbox"
            checked={values.include_out_of_network}
            onChange={(event) => handleFieldChange('include_out_of_network', event.target.checked)}
            disabled={disabled}
          />
          Include out-of-network facilities
        </label>
      </div>
      <div className="tc-structured-actions">
        <button type="submit" disabled={disabled || !values.cpt_code || !values.insurance || !values.zip}>
          Get Estimates
        </button>
      </div>
    </form>
  );
}
