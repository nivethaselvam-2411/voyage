import React, { useEffect, useState, useMemo } from 'react';
import { fetchRoutes } from '../services/api';
import type { RouteItem } from '../types';
import { DcrBadge } from '../components/DcrBadge';
import { TypeTag } from '../components/TypeTag';
import { ErrorState } from '../components/ErrorState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import {
  Search,
  ArrowUpDown
} from 'lucide-react';

interface FleetViewProps {
  isPanel?: boolean;
}

type SortField =
  | 'route_id'
  | 'actual_active_buses'
  | 'predicted_passengers'
  | 'predicted_demand_to_capacity_ratio'
  | 'overcrowding_risk_probability';

type FilterCategory = 'all' | 'over' | 'near' | 'balanced' | 'surplus';

export const FleetView: React.FC<FleetViewProps> = ({ isPanel = false }) => {
  const [routes, setRoutes] = useState<RouteItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Search, filter, and sort state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<FilterCategory>('all');
  const [sortField, setSortField] = useState<SortField>('predicted_demand_to_capacity_ratio');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRoutes();
      setRoutes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error fetching fleet routes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false); // default descending for metrics
    }
  };

  const filteredRoutes = useMemo(() => {
    return routes.filter((r) => {
      // Search across route ID, depot, origin, destination, corridor
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        r.route_id.toLowerCase().includes(q) ||
        (r.depot && r.depot.toLowerCase().includes(q)) ||
        (r.origin && r.origin.toLowerCase().includes(q)) ||
        (r.destination && r.destination.toLowerCase().includes(q)) ||
        (r.corridor && r.corridor.toLowerCase().includes(q));

      if (!matchesSearch) return false;

      // Category Filter
      const dcr = r.predicted_demand_to_capacity_ratio;
      if (categoryFilter === 'over') return dcr > 1.0;
      if (categoryFilter === 'near') return dcr > 0.85 && dcr <= 1.0;
      if (categoryFilter === 'balanced') return dcr > 0.40 && dcr <= 0.85;
      if (categoryFilter === 'surplus') return dcr <= 0.40;

      return true;
    });
  }, [routes, searchQuery, categoryFilter]);

  const sortedRoutes = useMemo(() => {
    return [...filteredRoutes].sort((a, b) => {
      let valA: any = a[sortField];
      let valB: any = b[sortField];

      if (sortField === 'route_id') {
        return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }

      valA = Number(valA) || 0;
      valB = Number(valB) || 0;
      return sortAsc ? valA - valB : valB - valA;
    });
  }, [filteredRoutes, sortField, sortAsc]);

  // Counts for tabs
  const counts = useMemo(() => {
    return {
      all: routes.length,
      over: routes.filter((r) => r.predicted_demand_to_capacity_ratio > 1.0).length,
      near: routes.filter((r) => r.predicted_demand_to_capacity_ratio > 0.85 && r.predicted_demand_to_capacity_ratio <= 1.0).length,
      balanced: routes.filter((r) => r.predicted_demand_to_capacity_ratio > 0.40 && r.predicted_demand_to_capacity_ratio <= 0.85).length,
      surplus: routes.filter((r) => r.predicted_demand_to_capacity_ratio <= 0.40).length
    };
  }, [routes]);

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
          marginBottom: '20px',
          borderBottom: 'var(--border-hairline)',
          paddingBottom: '16px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: isPanel ? '24px' : '28px', color: 'var(--color-ink)' }}>
              Fleet corridor overview
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
              {routes.length} corridors tracked
            </span>
          </div>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '13px', marginTop: '4px' }}>
            Corridor-level demand, active buses, and demand-to-capacity ratios across Chennai MTC routes.
          </p>
        </div>

        {/* Search input */}
        <div style={{ position: 'relative', width: isPanel ? '100%' : '280px' }}>
          <Search
            size={14}
            style={{
              position: 'absolute',
              left: '10px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--color-ink-muted)'
            }}
          />
          <input
            type="text"
            placeholder="Search route or depot..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: '100%', paddingLeft: '32px' }}
            aria-label="Search route number or depot"
          />
        </div>
      </div>

      {/* Filter Tabs */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px',
          marginBottom: '16px'
        }}
        role="tablist"
        aria-label="Corridor capacity categories"
      >
        {[
          { key: 'all', label: 'All corridors', count: counts.all },
          { key: 'over', label: 'Over capacity (> 1.0)', count: counts.over, color: 'var(--dcr-red)' },
          { key: 'near', label: 'Near capacity (0.85 - 1.0)', count: counts.near, color: 'var(--dcr-amber)' },
          { key: 'balanced', label: 'Balanced (0.41 - 0.85)', count: counts.balanced, color: 'var(--dcr-green)' },
          { key: 'surplus', label: 'Surplus donor (<= 0.40)', count: counts.surplus, color: 'var(--dcr-blue)' }
        ].map((tab) => {
          const isActive = categoryFilter === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setCategoryFilter(tab.key as FilterCategory)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: isActive ? 600 : 500,
                backgroundColor: isActive ? 'var(--color-panel-contrast)' : 'var(--color-panel)',
                border: isActive ? '1px solid var(--color-ink)' : 'var(--border-panel)',
                color: 'var(--color-ink)'
              }}
            >
              {tab.color && (
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: tab.color
                  }}
                />
              )}
              <span>{tab.label}</span>
              <span
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--color-ink-muted)'
                }}
              >
                ({tab.count})
              </span>
            </button>
          );
        })}
      </div>

      {/* Dense Bordered Data Table */}
      {loading && routes.length === 0 ? (
        <LoadingSkeleton rows={6} height={44} />
      ) : sortedRoutes.length === 0 ? (
        <div
          style={{
            padding: '32px',
            backgroundColor: 'var(--color-panel)',
            border: 'var(--border-panel)',
            textAlign: 'center',
            color: 'var(--color-ink-muted)'
          }}
        >
          No corridors match the search query or filter.
        </div>
      ) : (
        <div style={{ overflowX: 'auto', border: 'var(--border-panel)' }}>
          <table className="data-table" aria-label="Chennai MTC Fleet Corridor Data">
            <thead>
              <tr>
                <th
                  onClick={() => handleSort('route_id')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>Route</span>
                    <ArrowUpDown size={12} />
                  </div>
                </th>
                <th>Depot</th>
                <th
                  onClick={() => handleSort('actual_active_buses')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>Buses (Plan / Act)</span>
                    <ArrowUpDown size={12} />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('predicted_passengers')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>Hourly Pax (Pred / Act)</span>
                    <ArrowUpDown size={12} />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('predicted_demand_to_capacity_ratio')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>Predicted DCR</span>
                    <ArrowUpDown size={12} />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('overcrowding_risk_probability')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>Risk Probability</span>
                    <ArrowUpDown size={12} />
                  </div>
                </th>
                <th>Recommended action</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {sortedRoutes.map((route) => {
                const riskPct = Math.round(route.overcrowding_risk_probability * 100);

                return (
                  <tr key={route.route_id}>
                    {/* Route ID & Corridor */}
                    <td style={{ minWidth: '190px' }}>
                      <div style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                        Route {route.route_id}
                      </div>
                      {route.origin && route.destination && (
                        <div style={{ fontSize: '11px', color: 'var(--color-ink-muted)', marginTop: '2px' }}>
                          {route.origin} ↔ {route.destination}
                        </div>
                      )}
                      {route.corridor && (
                        <div style={{ fontSize: '10px', color: 'var(--color-accent-orange)', fontWeight: 600, marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                          {route.corridor}
                        </div>
                      )}
                    </td>

                    {/* Depot */}
                    <td style={{ color: 'var(--color-ink-muted)' }}>
                      {route.depot || 'n/a'}
                    </td>

                    {/* Buses Planned vs Active */}
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      <span style={{ fontWeight: 600 }}>{route.actual_active_buses}</span>
                      <span style={{ color: 'var(--color-ink-muted)', marginLeft: '4px' }}>
                        / {route.planned_buses_ex_ante}
                      </span>
                    </td>

                    {/* Passengers */}
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      <span>{route.predicted_passengers}</span>
                      <span style={{ color: 'var(--color-ink-muted)', marginLeft: '4px', fontSize: '11px' }}>
                        (act: {route.actual_passengers})
                      </span>
                    </td>

                    {/* Predicted DCR Chip */}
                    <td>
                      <DcrBadge dcr={route.predicted_demand_to_capacity_ratio} showLabel />
                    </td>

                    {/* Overcrowding Risk Probability */}
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '120px' }}>
                        <div
                          style={{
                            flex: 1,
                            height: '6px',
                            backgroundColor: '#DFE7EE',
                            borderRadius: 'var(--radius-sm)',
                            overflow: 'hidden'
                          }}
                        >
                          <div
                            style={{
                              width: `${riskPct}%`,
                              height: '100%',
                              backgroundColor: riskPct > 70 ? 'var(--dcr-red)' : riskPct > 40 ? 'var(--dcr-amber)' : 'var(--dcr-green)'
                            }}
                          />
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', width: '32px', textAlign: 'right' }}>
                          {riskPct}%
                        </span>
                      </div>
                    </td>

                    {/* Recommended action */}
                    <td style={{ fontSize: '12px', color: 'var(--color-ink)' }}>
                      {route.recommended_action}
                    </td>

                    {/* Type Tag */}
                    <td>
                      <TypeTag type={route.type ?? 'MEASURED'} size="sm" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Table Summary Footer */}
      <div
        style={{
          marginTop: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '11px',
          color: 'var(--color-ink-muted)',
          fontFamily: 'var(--font-mono)'
        }}
      >
        <span>Showing {sortedRoutes.length} of {routes.length} corridors</span>
        <span>Capacity assumption: 70 seats/bus</span>
      </div>
    </div>
  );
};
