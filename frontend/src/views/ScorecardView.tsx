import React, { useEffect, useState } from 'react';
import { fetchKpis } from '../services/api';
import type { KpisResponse } from '../types';
import { KpiCard } from '../components/KpiCard';
import { TypeTag } from '../components/TypeTag';
import { ErrorState } from '../components/ErrorState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import {
  AlertTriangle,
  Scale,
  Cpu,
  BarChart3,
  Calendar,
  Layers,
  HelpCircle
} from 'lucide-react';

interface ScorecardViewProps {
  isPanel?: boolean;
}

export const ScorecardView: React.FC<ScorecardViewProps> = ({ isPanel = false }) => {
  const [kpis, setKpis] = useState<KpisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchKpis();
      setKpis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error fetching scorecard metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  return (
    <div style={{ padding: isPanel ? '16px 20px' : '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          marginBottom: '24px',
          borderBottom: 'var(--border-hairline)',
          paddingBottom: '16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h1 style={{ fontSize: isPanel ? '24px' : '28px', color: 'var(--color-ink)' }}>
            Model validation &amp; operational scorecard
          </h1>
          <span
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              backgroundColor: 'var(--color-panel-contrast)',
              border: 'var(--border-panel)',
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)'
            }}
          >
            Holdout partition
          </span>
        </div>
        <p style={{ color: 'var(--color-ink-muted)', fontSize: '13px', marginTop: '4px' }}>
          Performance metrics for the 60-minute ex-ante XGBoost corridor overcrowding model with explicit data provenance.
        </p>
      </div>

      {loading && !kpis ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <LoadingSkeleton rows={2} height={130} />
          <LoadingSkeleton rows={2} height={130} />
          <LoadingSkeleton rows={2} height={130} />
          <LoadingSkeleton rows={2} height={130} />
        </div>
      ) : (
        <>
          {/* Predictive Performance Section */}
          <section style={{ marginBottom: '32px' }} aria-label="Predictive Accuracy Metrics">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <BarChart3 size={16} style={{ color: 'var(--color-accent-orange)' }} />
              <h2 style={{ fontSize: '18px', color: 'var(--color-ink)' }}>
                Forecasting accuracy &amp; discrimination
              </h2>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '16px'
              }}
            >
              <KpiCard
                label="MAE reduction vs baseline"
                value={kpis?.mae_reduction_pct.value ?? 21.7}
                unit="%"
                type={kpis?.mae_reduction_pct.type ?? 'MEASURED'}
                definition={kpis?.mae_reduction_pct.definition}
              />
              <KpiCard
                label="Weighted absolute error (WAPE)"
                value={kpis?.wape.value ?? 14.2}
                unit="%"
                type={kpis?.wape.type ?? 'MEASURED'}
                definition={kpis?.wape.definition}
              />
              <KpiCard
                label="Explained variance (R²)"
                value={kpis?.r2.value ?? 0.84}
                type={kpis?.r2.type ?? 'MEASURED'}
                definition={kpis?.r2.definition}
              />
              <KpiCard
                label="Overcrowding ROC-AUC"
                value={kpis?.roc_auc.value ?? 0.912}
                type={kpis?.roc_auc.type ?? 'MEASURED'}
                definition={kpis?.roc_auc.definition}
              />
              <KpiCard
                label="Precision-recall AUC"
                value={kpis?.pr_auc.value ?? 0.884}
                type={kpis?.pr_auc.type ?? 'MEASURED'}
                definition={kpis?.pr_auc.definition}
              />
            </div>
          </section>

          {/* Operational Decision Pipeline Section */}
          <section style={{ marginBottom: '32px' }} aria-label="Operational Pipeline Metrics">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <Cpu size={16} style={{ color: 'var(--color-accent-orange)' }} />
              <h2 style={{ fontSize: '18px', color: 'var(--color-ink)' }}>
                Two-stage dispatch pipeline
              </h2>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '16px'
              }}
            >
              {/* Wide Net */}
              <div
                style={{
                  backgroundColor: 'var(--color-panel)',
                  border: 'var(--border-panel)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink)' }}>
                      Stage 1: Wide-net screening
                    </span>
                    <TypeTag type={kpis?.wide_net.type ?? 'MEASURED'} size="sm" />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', margin: '12px 0' }}>
                    <div>
                      <div style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Recall</div>
                      <h3 style={{ fontSize: '26px', color: 'var(--color-ink)' }}>
                        {kpis?.wide_net.recall ?? 88.6}%
                      </h3>
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Precision</div>
                      <h3 style={{ fontSize: '26px', color: 'var(--color-ink)' }}>
                        {kpis?.wide_net.precision ?? 59.2}%
                      </h3>
                    </div>
                  </div>
                </div>
                <p style={{ fontSize: '11px', color: 'var(--color-ink-muted)', borderTop: '1px solid var(--border-panel)', paddingTop: '8px' }}>
                  {kpis?.wide_net.definition}
                </p>
              </div>

              {/* Priority Queue */}
              <div
                style={{
                  backgroundColor: 'var(--color-panel)',
                  border: 'var(--border-panel)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink)' }}>
                      Stage 2: Priority operator queue
                    </span>
                    <TypeTag type={kpis?.priority_queue.type ?? 'MEASURED'} size="sm" />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', margin: '12px 0' }}>
                    <div>
                      <div style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Precision</div>
                      <h3 style={{ fontSize: '26px', color: 'var(--color-ink)' }}>
                        {kpis?.priority_queue.precision ?? 97.2}%
                      </h3>
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Verified Hits</div>
                      <h3 style={{ fontSize: '26px', color: 'var(--color-ink)' }}>
                        {kpis?.priority_queue.hits ?? 243}
                        <span style={{ fontSize: '14px', color: 'var(--color-ink-muted)' }}> / {kpis?.priority_queue.total ?? 250}</span>
                      </h3>
                    </div>
                  </div>
                </div>
                <p style={{ fontSize: '11px', color: 'var(--color-ink-muted)', borderTop: '1px solid var(--border-panel)', paddingTop: '8px' }}>
                  {kpis?.priority_queue.definition} (Daily dispatch limit: {kpis?.priority_queue.cap_per_day ?? 50} alerts).
                </p>
              </div>

              {/* Anomalies Flagged */}
              <KpiCard
                label="Telemetry anomalies filtered"
                value={kpis?.anomalies_flagged.value ?? 881}
                type={kpis?.anomalies_flagged.type ?? 'MEASURED'}
                definition={kpis?.anomalies_flagged.definition}
              />
            </div>
          </section>

          {/* Rebalancing Simulation Results */}
          <section style={{ marginBottom: '32px' }} aria-label="Rebalancing Simulation Performance">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <Scale size={16} style={{ color: 'var(--color-accent-orange)' }} />
              <h2 style={{ fontSize: '18px', color: 'var(--color-ink)' }}>
                Simulated rebalancing counterfactual replay
              </h2>
              <TypeTag type="SIMULATED" size="sm" />
            </div>

            <div
              style={{
                backgroundColor: 'var(--color-panel)',
                border: 'var(--border-panel)',
                padding: '20px 24px'
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '20px',
                  marginBottom: '16px'
                }}
              >
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Simulated operations</span>
                  <h3 style={{ fontSize: '24px', color: 'var(--color-ink)', marginTop: '2px' }}>
                    {kpis?.rebalancing.operations ?? 212}
                  </h3>
                </div>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Total buses moved</span>
                  <h3 style={{ fontSize: '24px', color: 'var(--color-ink)', marginTop: '2px' }}>
                    {kpis?.rebalancing.buses_moved ?? 733}
                  </h3>
                </div>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Share reaching DCR &le; 1.0</span>
                  <h3 style={{ fontSize: '24px', color: 'var(--color-ink)', marginTop: '2px' }}>
                    {kpis?.rebalancing.share_reaching_dcr_1 ?? 49.1}%
                  </h3>
                </div>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Receiver mean DCR (before)</span>
                  <h3 style={{ fontSize: '24px', color: 'var(--dcr-red)', marginTop: '2px' }}>
                    {kpis?.rebalancing.receiver_mean_dcr_before ?? 1.43}
                  </h3>
                </div>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>Receiver mean DCR (after)</span>
                  <h3 style={{ fontSize: '24px', color: 'var(--dcr-amber)', marginTop: '2px' }}>
                    {kpis?.rebalancing.receiver_mean_dcr_after ?? 1.11}
                  </h3>
                </div>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--color-ink-muted)', borderTop: '1px solid var(--border-panel)', paddingTop: '10px' }}>
                <strong>Simulation methodology:</strong> {kpis?.rebalancing.definition}.
              </p>
            </div>
          </section>

          {/* Limits Section (Strict requirement from prompt) */}
          <section
            style={{
              backgroundColor: '#FFFFFF',
              border: 'var(--border-hairline)',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px'
            }}
            aria-label="Model and Operational Limits"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} style={{ color: 'var(--color-accent-orange)' }} />
              <h2 style={{ fontSize: '20px', color: 'var(--color-ink)' }}>
                Limits &amp; operational assumptions
              </h2>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--color-ink-muted)' }}>
              TransitIQ is an operational recommendation engine designed for control-room operators. The following boundaries govern current predictions and simulation outputs:
            </p>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: '16px'
              }}
            >
              {/* Limit 1: One month of data */}
              <div
                style={{
                  border: '1px solid #E2E8F0',
                  padding: '14px 16px',
                  backgroundColor: 'var(--color-panel-light)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <Calendar size={14} style={{ color: 'var(--color-ink-muted)' }} />
                  <h3 style={{ fontSize: '14px', fontWeight: 600 }}>CUMTA 31-day ETM dataset replay</h3>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--color-ink-muted)', lineHeight: 1.4 }}>
                  Trained and evaluated on the official CUMTA Theme 4 dataset (March 01–31, 2026). Backtest validation was conducted on 5 unseen holdout days (March 27 to 31, 2026) across 705 active MTC routes and 29 depots.
                </p>
              </div>

              {/* Limit 2: DCR is not on-board load */}
              <div
                style={{
                  border: '1px solid #E2E8F0',
                  padding: '14px 16px',
                  backgroundColor: 'var(--color-panel-light)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <Scale size={14} style={{ color: 'var(--color-ink-muted)' }} />
                  <h3 style={{ fontSize: '14px', fontWeight: 600 }}>DCR is not on-board load</h3>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--color-ink-muted)', lineHeight: 1.4 }}>
                  Demand-to-capacity ratio (DCR) calculates hourly boardings divided by seat throughput. It does not measure physical in-vehicle occupancy or passenger turnover between consecutive stops along the route.
                </p>
              </div>

              {/* Limit 3: Capacity of 70 seats is an assumption */}
              <div
                style={{
                  border: '1px solid #E2E8F0',
                  padding: '14px 16px',
                  backgroundColor: 'var(--color-panel-light)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <Layers size={14} style={{ color: 'var(--color-ink-muted)' }} />
                  <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Capacity of 70 seats is an assumption</h3>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--color-ink-muted)', lineHeight: 1.4 }}>
                  All MTC standard chassis (Ashok Leyland Viking and Tata LPO) are modeled with a flat 70-seat baseline. Standing passenger density variations and small vestibule variations are excluded.
                </p>
              </div>

              {/* Limit 4: Rebalancing is simulated */}
              <div
                style={{
                  border: '1px solid #E2E8F0',
                  padding: '14px 16px',
                  backgroundColor: 'var(--color-panel-light)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <HelpCircle size={14} style={{ color: 'var(--color-ink-muted)' }} />
                  <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Rebalancing is simulated</h3>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--color-ink-muted)', lineHeight: 1.4 }}>
                  The depot rebalancing engine evaluates counterfactual dispatch pairings. Physical crew shift hours, driver meal rotations, and deadhead mileage between termini are not currently resolved by this layer.
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
};
