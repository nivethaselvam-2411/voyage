import React, { useEffect, useState, useMemo } from 'react';
import { fetchRebalancePairs } from '../services/api';
import type { RebalancePair } from '../types';
import { DcrBadge } from '../components/DcrBadge';
import { ThinDcrBar } from '../components/ThinDcrBar';
import { TypeTag } from '../components/TypeTag';
import { ErrorState } from '../components/ErrorState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import {
  Building2,
  ArrowRight,
  Bus,
  Sliders,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck
} from 'lucide-react';

interface DepotsViewProps {
  isPanel?: boolean;
}

export const DepotsView: React.FC<DepotsViewProps> = ({ isPanel = false }) => {
  const [pairs, setPairs] = useState<RebalancePair[]>([]);
  const [selectedDepot, setSelectedDepot] = useState<string>('all');
  const [selectedPairIndex, setSelectedPairIndex] = useState<number>(0);
  const [busesMoved, setBusesMoved] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRebalancePairs();
      setPairs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error fetching rebalancing pairs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const depotsList = useMemo(() => {
    const set = new Set<string>();
    pairs.forEach((p) => {
      if (p.depot) set.add(p.depot);
    });
    return Array.from(set).sort();
  }, [pairs]);

  const filteredPairs = useMemo(() => {
    if (selectedDepot === 'all') return pairs;
    return pairs.filter((p) => p.depot.toLowerCase() === selectedDepot.toLowerCase());
  }, [pairs, selectedDepot]);

  // Keep index within bounds
  useEffect(() => {
    setSelectedPairIndex(0);
  }, [selectedDepot]);

  const activePair = filteredPairs[selectedPairIndex] || filteredPairs[0];

  // Reset or adjust slider when active pair changes
  useEffect(() => {
    if (activePair) {
      setBusesMoved(Math.min(1, activePair.k));
    }
  }, [activePair]);

  // Dynamic live recalculation derived strictly from formula:
  // new DCR = passengers / ((buses +/- moved) x 70)
  const calculation = useMemo(() => {
    if (!activePair) return null;

    const receiverPax =
      activePair.receiver_passengers ||
      Math.round(activePair.receiver_dcr_before * activePair.receiver_buses * 70);
    const donorPax =
      activePair.donor_passengers ||
      Math.round(activePair.donor_dcr_before * activePair.donor_buses * 70);

    const newReceiverBuses = activePair.receiver_buses + busesMoved;
    const newDonorBuses = Math.max(activePair.donor_buses - busesMoved, 1);

    const calculatedReceiverDcr = receiverPax / (newReceiverBuses * 70);
    const calculatedDonorDcr = donorPax / (newDonorBuses * 70);

    const isReceiverOverCapacity = calculatedReceiverDcr > 1.0;

    return {
      receiverPax,
      donorPax,
      newReceiverBuses,
      newDonorBuses,
      calculatedReceiverDcr,
      calculatedDonorDcr,
      isReceiverOverCapacity
    };
  }, [activePair, busesMoved]);

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  return (
    <div style={{ padding: isPanel ? '16px 20px' : '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          gap: '16px',
          marginBottom: '24px',
          borderBottom: 'var(--border-hairline)',
          paddingBottom: '16px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: isPanel ? '24px' : '28px', color: 'var(--color-ink)' }}>
              Depots &amp; fleet rebalancing
            </h1>
            <TypeTag type="SIMULATED" size="sm" />
          </div>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '13px', marginTop: '4px' }}>
            Simulate inter-route bus transfers from surplus donors (DCR &le; 0.40) to over capacity corridors.
          </p>
        </div>

        {/* Depot dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Building2 size={15} style={{ color: 'var(--color-ink-muted)' }} />
          <label htmlFor="depot-select" style={{ fontSize: '13px', color: 'var(--color-ink-muted)' }}>
            Depot:
          </label>
          <select
            id="depot-select"
            value={selectedDepot}
            onChange={(e) => setSelectedDepot(e.target.value)}
            style={{ minWidth: '180px' }}
          >
            <option value="all">All depots ({pairs.length} pairs)</option>
            {depotsList.map((depot) => (
              <option key={depot} value={depot}>
                {depot}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && pairs.length === 0 ? (
        <LoadingSkeleton rows={4} height={100} />
      ) : filteredPairs.length === 0 ? (
        <div
          style={{
            padding: '32px',
            backgroundColor: 'var(--color-panel)',
            border: 'var(--border-panel)',
            textAlign: 'center',
            color: 'var(--color-ink-muted)'
          }}
        >
          No rebalance candidate pairs found for the selected depot.
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: isPanel ? '1fr' : 'minmax(300px, 380px) 1fr',
            gap: '24px',
            alignItems: 'start'
          }}
        >
          {/* Pair Selection List */}
          <section
            aria-label="Available rebalance pairs"
            style={{
              maxHeight: isPanel ? 'none' : 'calc(100vh - 180px)',
              overflowY: isPanel ? 'visible' : 'auto',
              paddingRight: '8px'
            }}
          >
            <h2
              style={{
                fontSize: '16px',
                marginBottom: '12px',
                color: 'var(--color-ink)',
                position: 'sticky',
                top: 0,
                backgroundColor: 'var(--color-page)',
                zIndex: 2,
                paddingBottom: '6px'
              }}
            >
              Rebalance pairs ({filteredPairs.length})
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {filteredPairs.map((pair, idx) => {
                const isSelected = idx === selectedPairIndex;
                return (
                  <button
                    key={`${pair.depot}-${pair.receiver_route}-${pair.donor_route}-${idx}`}
                    type="button"
                    onClick={() => setSelectedPairIndex(idx)}
                    style={{
                      backgroundColor: isSelected ? 'var(--color-panel-contrast)' : 'var(--color-panel)',
                      border: isSelected ? '1px solid var(--color-ink)' : 'var(--border-panel)',
                      padding: '12px 14px',
                      textAlign: 'left',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      cursor: 'pointer',
                      width: '100%'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-ink-muted)' }}>
                        {pair.depot} Depot &bull; Hour {pair.hour}:00
                      </span>
                      <TypeTag type="SIMULATED" size="sm" />
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '14px' }}>
                          Rt {pair.receiver_route}
                        </span>
                        <DcrBadge dcr={pair.receiver_dcr_before} />
                      </div>

                      <ArrowRight size={14} style={{ color: 'var(--color-ink-muted)' }} />

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px', color: 'var(--color-ink-muted)' }}>
                          Rt {pair.donor_route}
                        </span>
                        <DcrBadge dcr={pair.donor_dcr_before} />
                      </div>
                    </div>

                    <div style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>
                      Movable capacity cap: up to {pair.k} buses
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Active Pair Simulation Studio */}
          {activePair && calculation && (
            <section
              style={{
                backgroundColor: 'var(--color-panel)',
                border: 'var(--border-panel)',
                padding: '24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '24px',
                position: isPanel ? 'static' : 'sticky',
                top: '20px',
                alignSelf: 'start'
              }}
              aria-label="Simulation configuration and recalculation"
            >
              {/* Header */}
              <div style={{ borderBottom: '1px solid var(--border-panel)', paddingBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--color-ink-muted)' }}>
                      Depot yard: {activePair.depot} | Date: {activePair.date} | Window: {activePair.hour}:00
                    </span>
                    <h2 style={{ fontSize: '22px', marginTop: '4px', color: 'var(--color-ink)' }}>
                      Transfer from Route {activePair.donor_route} to Route {activePair.receiver_route}
                    </h2>
                  </div>
                  <TypeTag type="SIMULATED" size="md" />
                </div>
              </div>

              {/* Interactive Bus Slider */}
              <div
                style={{
                  backgroundColor: 'var(--color-panel-light)',
                  border: 'var(--border-panel)',
                  padding: '16px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label htmlFor="buses-slider" style={{ fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sliders size={15} style={{ color: 'var(--color-accent-orange)' }} />
                    Buses moved (0 to {activePair.k}):
                  </label>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '18px',
                      fontWeight: 700,
                      color: 'var(--color-accent-orange)',
                      backgroundColor: '#FFFFFF',
                      padding: '2px 10px',
                      border: 'var(--border-hairline)',
                      borderRadius: 'var(--radius-sm)'
                    }}
                  >
                    {busesMoved} {busesMoved === 1 ? 'bus' : 'buses'}
                  </span>
                </div>

                <input
                  id="buses-slider"
                  type="range"
                  min={0}
                  max={activePair.k}
                  step={1}
                  value={busesMoved}
                  onChange={(e) => setBusesMoved(Number(e.target.value))}
                  style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--color-accent-orange)' }}
                  aria-label="Number of buses to shift"
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-ink-muted)' }}>
                  <span>0 (No dispatch)</span>
                  <span>Max allowable: {activePair.k} chassis</span>
                </div>
              </div>

              {/* Live Before / After Comparison Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                {/* Receiver Route */}
                <div
                  style={{
                    backgroundColor: '#FFFFFF',
                    border: 'var(--border-hairline)',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-muted)', fontWeight: 600 }}>
                        Receiver Route
                      </span>
                      <h3 style={{ fontSize: '18px', marginTop: '2px' }}>Route {activePair.receiver_route}</h3>
                    </div>
                    <Bus size={18} style={{ color: 'var(--color-ink-muted)' }} />
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--color-ink-muted)' }}>
                    Boarding demand: <strong style={{ color: 'var(--color-ink)' }}>{calculation.receiverPax} pax/hr</strong>
                  </div>

                  {/* Before */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px' }}>
                      <span style={{ color: 'var(--color-ink-muted)' }}>Before: {activePair.receiver_buses} buses</span>
                      <DcrBadge dcr={activePair.receiver_dcr_before} />
                    </div>
                    <ThinDcrBar dcr={activePair.receiver_dcr_before} height={6} showMarker={false} />
                  </div>

                  {/* After Live */}
                  <div style={{ borderTop: '1px dashed #E2E8F0', paddingTop: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>
                        Live simulated: {calculation.newReceiverBuses} buses (+{busesMoved})
                      </span>
                      <DcrBadge dcr={calculation.calculatedReceiverDcr} showLabel />
                    </div>
                    <ThinDcrBar dcr={calculation.calculatedReceiverDcr} height={8} />
                  </div>
                </div>

                {/* Donor Route */}
                <div
                  style={{
                    backgroundColor: '#FFFFFF',
                    border: 'var(--border-hairline)',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-muted)', fontWeight: 600 }}>
                        Donor Route
                      </span>
                      <h3 style={{ fontSize: '18px', marginTop: '2px' }}>Route {activePair.donor_route}</h3>
                    </div>
                    <ShieldCheck size={18} style={{ color: 'var(--dcr-blue)' }} />
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--color-ink-muted)' }}>
                    Boarding demand: <strong style={{ color: 'var(--color-ink)' }}>{calculation.donorPax} pax/hr</strong>
                  </div>

                  {/* Before */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px' }}>
                      <span style={{ color: 'var(--color-ink-muted)' }}>Before: {activePair.donor_buses} buses</span>
                      <DcrBadge dcr={activePair.donor_dcr_before} />
                    </div>
                    <ThinDcrBar dcr={activePair.donor_dcr_before} height={6} showMarker={false} />
                  </div>

                  {/* After Live */}
                  <div style={{ borderTop: '1px dashed #E2E8F0', paddingTop: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>
                        Live simulated: {calculation.newDonorBuses} buses (-{busesMoved})
                      </span>
                      <DcrBadge dcr={calculation.calculatedDonorDcr} showLabel />
                    </div>
                    <ThinDcrBar dcr={calculation.calculatedDonorDcr} height={8} />
                  </div>
                </div>
              </div>

              {/* Required Plain Note */}
              <div
                style={{
                  padding: '12px 16px',
                  backgroundColor: calculation.isReceiverOverCapacity ? '#FFFBEB' : '#F0FDF4',
                  border: calculation.isReceiverOverCapacity ? '1px solid #FDE68A' : '1px solid #BBF7D0',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}
              >
                {calculation.isReceiverOverCapacity ? (
                  <>
                    <AlertTriangle size={16} style={{ color: 'var(--dcr-amber)', flexShrink: 0 }} />
                    <span style={{ color: 'var(--color-ink)' }}>
                      <strong>partly relieved: donor service is protected</strong> (simulated receiver DCR remains at{' '}
                      {calculation.calculatedReceiverDcr.toFixed(2)}, donor DCR reaches{' '}
                      {calculation.calculatedDonorDcr.toFixed(2)} &le; 0.85).
                    </span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={16} style={{ color: 'var(--dcr-green)', flexShrink: 0 }} />
                    <span style={{ color: 'var(--color-ink)' }}>
                      <strong>overcrowding resolved: donor service is protected</strong> (simulated receiver DCR drops to{' '}
                      {calculation.calculatedReceiverDcr.toFixed(2)} &le; 1.0, donor DCR is healthy at{' '}
                      {calculation.calculatedDonorDcr.toFixed(2)}).
                    </span>
                  </>
                )}
              </div>

              {/* Calculation Formula Transparency */}
              <div
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--color-ink-muted)',
                  backgroundColor: 'var(--color-panel-light)',
                  padding: '10px 14px',
                  border: '1px solid var(--border-panel)'
                }}
              >
                <div>Formula: new DCR = hourly boardings / ((active buses &plusmn; moved) &times; 70 seats)</div>
                <div style={{ marginTop: '2px' }}>
                  Receiver: {calculation.receiverPax} / ({calculation.newReceiverBuses} &times; 70) ={' '}
                  {calculation.calculatedReceiverDcr.toFixed(3)} | Donor: {calculation.donorPax} / ({calculation.newDonorBuses} &times; 70) ={' '}
                  {calculation.calculatedDonorDcr.toFixed(3)}
                </div>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
};

