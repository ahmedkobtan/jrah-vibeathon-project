import type {
  EstimateResponse,
  FacilityEstimate,
  ServiceEstimate
} from '../services/apiClient';

type Props = {
  data?: EstimateResponse;
};

export function ResultList({ data }: Props) {
  if (!data || Object.keys(data.results).length === 0) {
    return <p className="tc-empty">No estimates yet. Try searching for a procedure.</p>;
  }

  return (
    <div className="tc-results">
      {Object.entries(data.results).map(([state, facilities]) => (
        <section key={state} className="tc-state-group">
          <header className="tc-state-header">
            <h3>{state}</h3>
          </header>
          <ul className="tc-facilities">
            {facilities.map((facility) => (
              <FacilityCard key={facility.facility} facility={facility} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

type FacilityCardProps = {
  facility: FacilityEstimate;
};

function FacilityCard({ facility }: FacilityCardProps) {
  const { distance_miles, services, source, confidence, coverage_percent } = facility;
  return (
    <li className="tc-facility-card">
      <div className="tc-facility-header">
        <h4>{facility.facility}</h4>
        {distance_miles != null ? <span className="tc-distance">{distance_miles.toFixed(1)} mi</span> : null}
      </div>
      <dl className="tc-services">
        {services.map((service) => (
          <ServiceRow key={service.cpt_code} service={service} />
        ))}
      </dl>
      <footer className="tc-meta">
        {source ? <span className="tc-badge">{source}</span> : null}
        {confidence != null ? (
          <span className="tc-meta-text">confidence {(confidence * 100).toFixed(0)}%</span>
        ) : null}
        {coverage_percent != null ? (
          <span className="tc-meta-text">coverage {(coverage_percent * 100).toFixed(0)}%</span>
        ) : null}
      </footer>
    </li>
  );
}

type ServiceRowProps = {
  service: ServiceEstimate;
};

function ServiceRow({ service }: ServiceRowProps) {
  return (
    <div className="tc-service-row">
      <dt>
        CPT {service.cpt_code}
        {service.patient_responsibility != null ? (
          <span className="tc-patient-share"> · patient ≈ ${service.patient_responsibility.toFixed(0)}</span>
        ) : null}
      </dt>
      <dd>${service.negotiated_rate.toFixed(0)}</dd>
    </div>
  );
}
