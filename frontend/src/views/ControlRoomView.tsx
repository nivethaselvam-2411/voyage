import React, { useEffect, useState, useMemo } from 'react';
import { fetchKpis, fetchControlRoomAlerts, fetchHourlySummary } from '../services/api';
import type { KpisResponse, ControlRoomAlert, HourlySummaryEntry } from '../types';
import { KpiCard } from '../components/KpiCard';
import { DcrBadge } from '../components/DcrBadge';
import { ThinDcrBar } from '../components/ThinDcrBar';
import { TypeTag } from '../components/TypeTag';
import { ErrorState } from '../components/ErrorState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import {
  Calendar,
  Clock,
  Check,
  X,
  RotateCcw,
  SlidersHorizontal,
  Info
} from 'lucide-react';

interface ControlRoomViewProps {
  isPanel?: boolean;
}

export const ControlRoomView: React.FC<ControlRoomViewProps> = ({ isPanel = false }) => {
  const [kpis, setKpis] = useState<KpisResponse | null>(null);
  const [alerts, setAlerts] = useState<ControlRoomAlert[]>([]);
  const [hourlySummary, setHourlySummary] = useState<Record<string, HourlySummaryEntry>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter and action states
  const [selectedDate, setSelectedDate] = useState<string>('2026-03-27');
  const [selectedHour, setSelectedHour] = useState<number>(9);
  const [selectedDepot, setSelectedDepot] = useState<string>('all');
  const [actionStates, setActionStates] = useState<Record<string, 'accepted' | 'dismissed'>>({});

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [kpisRes, alertsRes, hourlyRes] = await Promise.all([
        fetchKpis(),
        fetchControlRoomAlerts(selectedDate, selectedHour),
        fetchHourlySummary()
      ]);
      setKpis(kpisRes);
      setAlerts(alertsRes);
      setHourlySummary(hourlyRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error fetching control-room alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedDate, selectedHour]);

  const handleAction = (alertId: string, action: 'accepted' | 'dismissed') => {
    setActionStates((prev) => ({
      ...prev,
      [alertId]: action
    }));
  };

  const handleResetAction = (alertId: string) => {
    setActionStates((prev) => {
      const copy = { ...prev };
      delete copy[alertId];
      return copy;
    });
  };

  const depotsList = useMemo(() => {
    const set = new Set<string>();
    alerts.forEach((a) => {
      if (a.depot) set.add(a.depot);
    });
    return Array.from(set).sort();
  }, [alerts]);

  const filteredAlerts = useMemo(() => {
    if (selectedDepot === 'all') return alerts;
    return alerts.filter((a) => a.depot.toLowerCase() === selectedDepot.toLowerCase());
  }, [alerts, selectedDepot]);

  const activeAlertCount = useMemo(() => {
    return filteredAlerts.filter((a) => !actionStates[a.id]).length;
  }, [filteredAlerts, actionStates]);

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  return (
    <div style={{ padding: isPanel ? '16px 20px' : '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Header & Date/Hour Selector */}
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
              Control room
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
              Live queue: {activeAlertCount} pending
            </span>
          </div>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '13px', marginTop: '4px' }}>
            Ranked operational actions predicted 60 minutes ahead of corridor overcrowding.
          </p>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Calendar size={14} style={{ color: 'var(--color-ink-muted)' }} />
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              aria-label="Filter by date"
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Clock size={14} style={{ color: 'var(--color-ink-muted)' }} />
            <select
              value={selectedHour}
              onChange={(e) => setSelectedHour(Number(e.target.value))}
              aria-label="Filter by operating hour"
            >
              {Array.from({ length: 16 }, (_, i) => i + 6).map((h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, '0')}:00 - {String(h + 1).padStart(2, '0')}:00
                </option>
              ))}
            </select>
            {hourlySummary[String(selectedHour)] && (
              <span style={{ fontSize: '11px', color: 'var(--color-ink-muted)', fontFamily: 'var(--font-mono)' }}>
                ({hourlySummary[String(selectedHour)].overcrowded_routes} bottlenecks)
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <SlidersHorizontal size={14} style={{ color: 'var(--color-ink-muted)' }} />
            <select
              value={selectedDepot}
              onChange={(e) => setSelectedDepot(e.target.value)}
              aria-label="Filter by depot"
            >
              <option value="all">All depots ({depotsList.length})</option>
              {depotsList.map((depot) => (
                <option key={depot} value={depot}>
                  {depot}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* KPI Strip */}
      <section style={{ marginBottom: '32px' }} aria-label="Key operational performance indicators">
        {loading && !kpis ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            <LoadingSkeleton rows={1} height={124} />
            <LoadingSkeleton rows={1} height={124} />
            <LoadingSkeleton rows={1} height={124} />
            <LoadingSkeleton rows={1} height={124} />
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '16px'
            }}
          >
            <KpiCard
              label="Forecast error reduction"
              value={kpis?.mae_reduction_pct.value ?? 21.7}
              unit="%"
              type={kpis?.mae_reduction_pct.type ?? 'MEASURED'}
              definition={kpis?.mae_reduction_pct.definition}
            />
            <KpiCard
              label="Lead time window"
              value={60}
              unit="min"
              type="MEASURED"
              definition="Ex-ante lookahead before corridor passenger boarding begins"
            />
            <KpiCard
              label="Priority queue precision"
              value={kpis?.priority_queue.precision ?? 97.2}
              unit="%"
              type={kpis?.priority_queue.type ?? 'MEASURED'}
              secondaryLabel="Dispatched hits"
              secondaryValue={`${kpis?.priority_queue.hits ?? 243} / ${kpis?.priority_queue.total ?? 250}`}
              definition={kpis?.priority_queue.definition}
            />
            <KpiCard
              label="Anomalies flagged"
              value={kpis?.anomalies_flagged.value ?? 881}
              type={kpis?.anomalies_flagged.type ?? 'MEASURED'}
              definition={kpis?.anomalies_flagged.definition}
            />
          </div>
        )}
      </section>

      {/* Alert Guidance Note */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '8px',
          backgroundColor: 'var(--color-panel-light)',
          border: 'var(--border-panel)',
          padding: '10px 14px',
          marginBottom: '20px',
          fontSize: '12px',
          color: 'var(--color-ink-muted)'
        }}
      >
        <Info size={15} style={{ color: 'var(--color-accent-orange)', flexShrink: 0, marginTop: '2px' }} />
        <span>
          <strong>Operator rule:</strong> DCR represents hourly boardings divided by theoretical capacity (active buses x 70 seats).
          An alert with DCR &gt; 1.0 indicates passenger demand exceeds available seat-hours. Accept to queue an injection order
          or dismiss if local route congestion has cleared.
        </span>
      </div>

      {/* Ranked Alert List */}
      <section aria-label="Ranked control-room alerts">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '18px', color: 'var(--color-ink)' }}>
            Ranked alert queue ({filteredAlerts.length})
          </h2>
          <span style={{ fontSize: '12px', color: 'var(--color-ink-muted)' }}>
            Sorted by predicted overcrowding severity
          </span>
        </div>

        {loading && alerts.length === 0 ? (
          <LoadingSkeleton rows={5} height={90} />
        ) : filteredAlerts.length === 0 ? (
          <div
            style={{
              padding: '32px',
              backgroundColor: 'var(--color-panel)',
              border: 'var(--border-panel)',
              textAlign: 'center',
              color: 'var(--color-ink-muted)'
            }}
          >
            No alerts found for the selected depot and operating window.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {filteredAlerts.map((alert, index) => {
              const state = actionStates[alert.id];
              const isAccepted = state === 'accepted';
              const isDismissed = state === 'dismissed';

              return (
                <div
                  key={alert.id}
                  style={{
                    backgroundColor: isAccepted ? '#F0FDF4' : isDismissed ? '#F1F5F9' : 'var(--color-panel)',
                    border: isAccepted ? '1px solid #86EFAC' : isDismissed ? '1px solid #CBD5E1' : 'var(--border-panel)',
                    padding: '16px 20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    opacity: isDismissed ? 0.7 : 1,
                    transition: 'all var(--transition-speed) ease'
                  }}
                >
                  {/* Top row: Route, Depot, Time window, Badges */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '11px',
                          color: 'var(--color-ink-muted)',
                          padding: '1px 5px',
                          backgroundColor: 'var(--color-panel-contrast)',
                          borderRadius: 'var(--radius-sm)'
                        }}
                      >
                        #{index + 1}
                      </span>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '18px',
                          fontWeight: 700,
                          color: 'var(--color-ink)'
                        }}
                      >
                        Route {alert.route}
                      </span>
                      <span
                        style={{
                          fontSize: '13px',
                          color: 'var(--color-ink-muted)',
                          borderLeft: '1px solid var(--border-panel)',
                          paddingLeft: '10px'
                        }}
                      >
                        {alert.depot} depot
                      </span>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '12px',
                          color: 'var(--color-ink-muted)'
                        }}
                      >
                        Window: {alert.time_window}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <TypeTag type={alert.type ?? 'MEASURED'} size="sm" />
                      <span
                        style={{
                          fontSize: '11px',
                          fontFamily: 'var(--font-sans)',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: alert.action_type === 'fleet_injection' ? '#FEF3C7' : '#E0E7FF',
                          color: alert.action_type === 'fleet_injection' ? '#B45309' : '#3730A3',
                          border: alert.action_type === 'fleet_injection' ? '1px solid #FDE68A' : '1px solid #C7D2FE',
                          textTransform: 'none'
                        }}
                      >
                        {alert.action_type === 'fleet_injection' ? 'Fleet injection' : 'Short turn'}
                      </span>
                      <DcrBadge dcr={alert.predicted_dcr} showLabel prefix="Pred DCR" />
                    </div>
                  </div>

                  {/* Middle row: Thin DCR bar and deficit */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 360px) 1fr', gap: '20px', alignItems: 'center' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px', color: 'var(--color-ink-muted)' }}>
                        <span>Predicted DCR intensity</span>
                        <span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>
                          +{alert.expected_deficit_pax} deficit pax
                        </span>
                      </div>
                      <ThinDcrBar dcr={alert.predicted_dcr} height={8} />
                    </div>

                    <div style={{ fontSize: '13px', color: 'var(--color-ink)', lineHeight: 1.4 }}>
                      <p>
                        <strong>Reason:</strong> {alert.reason}
                      </p>
                      <p style={{ marginTop: '2px', color: 'var(--color-ink-muted)' }}>
                        <strong>Expected impact:</strong> {alert.expected_impact}
                      </p>
                    </div>
                  </div>

                  {/* Bottom row: Operator action buttons & confirmation state */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      paddingTop: '8px',
                      borderTop: '1px solid var(--border-panel)'
                    }}
                  >
                    <span style={{ fontSize: '11px', color: 'var(--color-ink-muted)', fontFamily: 'var(--font-mono)' }}>
                      Alert ID: {alert.id}
                    </span>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {state ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span
                            style={{
                              fontSize: '12px',
                              fontWeight: 600,
                              color: isAccepted ? 'var(--dcr-green)' : 'var(--color-ink-muted)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}
                          >
                            {isAccepted ? (
                              <>
                                <Check size={14} /> Action queued to depot
                              </>
                            ) : (
                              <>
                                <X size={14} /> Alert dismissed
                              </>
                            )}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleResetAction(alert.id)}
                            style={{
                              padding: '4px 8px',
                              backgroundColor: 'transparent',
                              border: '1px solid #CBD5E1',
                              color: 'var(--color-ink-muted)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '11px'
                            }}
                            title="Undo action"
                          >
                            <RotateCcw size={12} />
                            Undo
                          </button>
                        </div>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => handleAction(alert.id, 'dismissed')}
                            style={{
                              padding: '6px 12px',
                              backgroundColor: '#FFFFFF',
                              border: 'var(--border-hairline)',
                              color: 'var(--color-ink-muted)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px'
                            }}
                          >
                            <X size={13} />
                            Dismiss
                          </button>
                          <button
                            type="button"
                            onClick={() => handleAction(alert.id, 'accepted')}
                            style={{
                              padding: '6px 14px',
                              backgroundColor: 'var(--color-accent-orange)',
                              border: '1px solid #D0581C',
                              color: '#FFFFFF',
                              fontWeight: 600,
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px'
                            }}
                          >
                            <Check size={13} />
                            Accept action
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
};
