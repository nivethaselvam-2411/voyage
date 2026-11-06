import React, { useEffect, useState, useRef, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchLiveNetwork } from '../services/api';
import type { LiveNetworkResponse, LiveBus, LiveCorridor, TransferStop } from '../types';
import { DcrBadge } from '../components/DcrBadge';
import { ErrorState } from '../components/ErrorState';
import { Search } from 'lucide-react';

interface LiveMapViewProps {
  isPanel?: boolean;
}

export const LiveMapView: React.FC<LiveMapViewProps> = ({ isPanel = false }) => {
  const [data, setData] = useState<LiveNetworkResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState<boolean>(false);

  // Filters & Selection
  const [selectedRoute, setSelectedRoute] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedDelay, setSelectedDelay] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedBusId, setSelectedBusId] = useState<string | null>(null);
  const [showStops, setShowStops] = useState<boolean>(true);
  const [showCorridors, setShowCorridors] = useState<boolean>(true);

  // Map Refs
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const busLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const corridorLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const stopsLayerGroupRef = useRef<L.LayerGroup | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchLiveNetwork();
      setData(res);
      if (res.buses && res.buses.length > 0 && !selectedBusId) {
        setSelectedBusId(res.buses[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading live transit network');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filtered buses list
  const filteredBuses = useMemo(() => {
    if (!data?.buses) return [];
    return data.buses.filter((bus: LiveBus) => {
      const matchesRoute = selectedRoute === 'all' || bus.route.toLowerCase() === selectedRoute.toLowerCase();
      const matchesStatus = selectedStatus === 'all' || bus.status === selectedStatus;
      const matchesDelay = selectedDelay === 'all' || bus.delay_status === selectedDelay;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        bus.fleet_no.toLowerCase().includes(q) ||
        bus.route.toLowerCase().includes(q) ||
        bus.route_name.toLowerCase().includes(q) ||
        bus.depot.toLowerCase().includes(q);
      return matchesRoute && matchesStatus && matchesDelay && matchesSearch;
    });
  }, [data, selectedRoute, selectedStatus, selectedDelay, searchQuery]);

  const selectedBus = useMemo(() => {
    if (!data?.buses) return null;
    return data.buses.find((b: LiveBus) => b.id === selectedBusId) || data.buses[0] || null;
  }, [data, selectedBusId]);

  // Initialize Leaflet Map once on mount
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const container = mapContainerRef.current;
    // Clear any residual Leaflet instance ID on the DOM node (e.g. from Vite hot reload)
    if ((container as unknown as { _leaflet_id?: number })._leaflet_id) {
      delete (container as unknown as { _leaflet_id?: number })._leaflet_id;
    }

    // Centered on Chennai arterial grid: 13.04 N, 80.22 E
    const map = L.map(container, {
      center: [13.04, 80.22],
      zoom: 11,
      minZoom: 9,
      maxZoom: 18,
      zoomControl: true,
      preferCanvas: true
    });

    // OpenStreetMap standard tile layer - 100% free, no API key required, zero watermarks
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      subdomains: ['a', 'b', 'c'],
      maxZoom: 19
    }).addTo(map);

    corridorLayerGroupRef.current = L.layerGroup().addTo(map);
    stopsLayerGroupRef.current = L.layerGroup().addTo(map);
    busLayerGroupRef.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;
    setMapReady(true);

    // Call invalidateSize after container has painted its dimensions
    const t1 = setTimeout(() => {
      map.invalidateSize();
    }, 150);
    const t2 = setTimeout(() => {
      map.invalidateSize();
    }, 500);

    const handleResize = () => {
      map.invalidateSize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener('resize', handleResize);
      map.remove();
      mapInstanceRef.current = null;
      corridorLayerGroupRef.current = null;
      stopsLayerGroupRef.current = null;
      busLayerGroupRef.current = null;
      setMapReady(false);
    };
  }, []);

  // Invalidate map size whenever data or layout changes
  useEffect(() => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.invalidateSize();
    }
  }, [loading, data, mapReady]);

  // Render Corridors on Map
  useEffect(() => {
    const layer = corridorLayerGroupRef.current;
    if (!layer || !data?.corridors) return;
    layer.clearLayers();

    if (!showCorridors) return;

    data.corridors.forEach((corr: LiveCorridor) => {
      if (selectedRoute !== 'all' && corr.route_id.toLowerCase() !== selectedRoute.toLowerCase()) {
        return;
      }
      const poly = L.polyline(corr.waypoints, {
        color: corr.color || '#2563EB',
        weight: selectedRoute === corr.route_id ? 5 : 3.5,
        opacity: selectedRoute === corr.route_id ? 0.95 : 0.7,
        lineCap: 'round',
        lineJoin: 'round'
      });
      poly.bindTooltip(`<b>Route ${corr.route_id}</b><br/>${corr.name}`, { sticky: true });
      layer.addLayer(poly);
    });
  }, [mapReady, data, selectedRoute, showCorridors]);

  // Render Major Transfer Stops on Map
  useEffect(() => {
    const layer = stopsLayerGroupRef.current;
    if (!layer || !data?.transfer_stops) return;
    layer.clearLayers();

    if (!showStops) return;

    data.transfer_stops.forEach((stop: TransferStop) => {
      const stopIcon = L.divIcon({
        className: 'custom-stop-icon',
        html: `<div style="
          width: 8px;
          height: 8px;
          background: #0F172A;
          border: 2px solid #FFFFFF;
          border-radius: 50%;
          box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        "></div>`,
        iconSize: [8, 8],
        iconAnchor: [4, 4]
      });

      const marker = L.marker([stop.lat, stop.lon], { icon: stopIcon });
      marker.bindTooltip(`<b>${stop.name}</b><br/><span style="color:#64748B">${stop.type}</span>`, {
        direction: 'top',
        offset: [0, -4]
      });
      layer.addLayer(marker);
    });
  }, [mapReady, data, showStops]);

  // Render Buses with Live Passenger Load & Predicted Delays
  useEffect(() => {
    const layer = busLayerGroupRef.current;
    if (!layer || !filteredBuses) return;
    layer.clearLayers();

    filteredBuses.forEach((bus: LiveBus) => {
      const isSelected = bus.id === selectedBusId;

      // Color coding based on occupancy status
      let badgeBg = '#16A34A'; // Balanced
      if (bus.status === 'critical') badgeBg = '#DC2626'; // Overcrowded
      else if (bus.status === 'crowded') badgeBg = '#D97706'; // Near-Capacity
      else if (bus.status === 'surplus') badgeBg = '#64748B'; // Surplus

      // Delay indicator pill
      const delayColor =
        bus.delay_status === 'severe'
          ? '#991B1B'
          : bus.delay_status === 'moderate'
          ? '#B45309'
          : '#15803D';

      const busHtml = `
        <div style="
          display: flex;
          align-items: center;
          gap: 4px;
          background-color: ${badgeBg};
          color: #FFFFFF;
          font-family: var(--font-mono, monospace);
          font-size: 11px;
          font-weight: 700;
          padding: ${isSelected ? '3px 8px' : '2px 6px'};
          border-radius: 12px;
          border: ${isSelected ? '2.5px solid #0F172A' : '1.5px solid #FFFFFF'};
          box-shadow: ${isSelected ? '0 0 0 3px rgba(37,99,235,0.4), 0 3px 8px rgba(0,0,0,0.35)' : '0 2px 4px rgba(0,0,0,0.25)'};
          white-space: nowrap;
          cursor: pointer;
          transform: ${isSelected ? 'scale(1.15)' : 'scale(1.0)'};
          transition: transform 0.15s ease;
        ">
          <span style="font-size: 10px;">🚌</span>
          <span>${bus.route}</span>
          <span style="background: rgba(0,0,0,0.25); padding: 1px 4px; border-radius: 6px; font-size: 10px;">
            ${bus.passengers}p
          </span>
          <span style="background: ${delayColor}; padding: 1px 4px; border-radius: 6px; font-size: 9px;">
            +${Math.round(bus.predicted_delay_min)}m
          </span>
        </div>
      `;

      const busIcon = L.divIcon({
        className: 'custom-bus-marker',
        html: busHtml,
        iconSize: [85, 24],
        iconAnchor: [42, 12]
      });

      const marker = L.marker([bus.lat, bus.lng], { icon: busIcon, zIndexOffset: isSelected ? 1000 : 100 });
      marker.on('click', () => {
        setSelectedBusId(bus.id);
        if (mapInstanceRef.current) {
          mapInstanceRef.current.panTo([bus.lat, bus.lng], { animate: true, duration: 0.4 });
        }
      });

      marker.bindTooltip(
        `<b>${bus.fleet_no}</b> (Rt ${bus.route})<br/><b>${bus.passengers} Passengers</b> (${bus.dcr}x DCR)<br/>Predicted Delay: <b>+${bus.predicted_delay_min} min (${bus.delay_status.toUpperCase()})</b><br/>Expected Arrival: <b>${bus.predicted_arrival_time}</b>`,
        { direction: 'top', offset: [0, -12] }
      );

      layer.addLayer(marker);
    });
  }, [mapReady, filteredBuses, selectedBusId]);

  const handleSelectBus = (bus: LiveBus) => {
    setSelectedBusId(bus.id);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([bus.lat, bus.lng], 13, { animate: true });
    }
  };

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  const summary = data?.summary;

  return (
    <div style={{ padding: isPanel ? '12px 16px' : '20px 28px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Header & Metrics Strip */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          marginBottom: '16px',
          borderBottom: 'var(--border-hairline)',
          paddingBottom: '12px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: isPanel ? '22px' : '26px', color: 'var(--color-ink)' }}>
              Chennai live transit map
            </h1>
            <span
              style={{
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                backgroundColor: '#DC2626',
                color: '#FFFFFF',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                fontWeight: 700
              }}
            >
              LIVE TELEMETRY REPLAY
            </span>
            <span style={{ fontSize: '12px', color: 'var(--color-ink-muted)', fontFamily: 'var(--font-mono)' }}>
              {data?.simulated_time || '08:30 AM'}
            </span>
          </div>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '13px', marginTop: '2px' }}>
            Real-time passenger load profiles derived from ETM boarding-alighting conservation law + 60-min ex-ante delay prediction.
          </p>
        </div>

        {/* Network Metrics Badges */}
        {summary && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div style={{ backgroundColor: 'var(--color-panel)', border: 'var(--border-panel)', padding: '6px 12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '10px', color: 'var(--color-ink-muted)' }}>Active Buses</div>
              <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{summary.active_buses_tracked}</div>
            </div>
            <div style={{ backgroundColor: 'var(--color-panel)', border: 'var(--border-panel)', padding: '6px 12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '10px', color: 'var(--color-ink-muted)' }}>Passengers Onboard</div>
              <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-accent-orange)' }}>
                {summary.total_passengers_in_transit.toLocaleString()}
              </div>
            </div>
            <div style={{ backgroundColor: '#FEF2F2', border: '1px solid #FCA5A5', padding: '6px 12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '10px', color: '#B91C1C' }}>Critical Overcrowded</div>
              <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#DC2626' }}>
                {summary.critical_overcrowded} <span style={{ fontSize: '11px', fontWeight: 400 }}>buses</span>
              </div>
            </div>
            {/* Predicted Delay Badge */}
            <div style={{ backgroundColor: '#FFFBEB', border: '1px solid #FCD34D', padding: '6px 12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '10px', color: '#B45309' }}>Avg Predicted Delay</div>
              <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#D97706' }}>
                +{summary.avg_predicted_delay_min} <span style={{ fontSize: '11px', fontWeight: 400 }}>min</span>
              </div>
            </div>
            <div style={{ backgroundColor: 'var(--color-panel)', border: 'var(--border-panel)', padding: '6px 12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '10px', color: 'var(--color-ink-muted)' }}>Avg Corridor DCR</div>
              <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{summary.network_avg_dcr}x</div>
            </div>
          </div>
        )}
      </div>

      {/* Filter and Control Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '14px',
          backgroundColor: 'var(--color-panel)',
          border: 'var(--border-panel)',
          padding: '10px 14px',
          borderRadius: 'var(--radius-sm)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Corridor Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600 }}>Corridor:</span>
            <select
              value={selectedRoute}
              onChange={(e) => setSelectedRoute(e.target.value)}
              style={{ fontSize: '12px', padding: '4px 8px' }}
            >
              <option value="all">All Corridors (8 major arterial routes)</option>
              {data?.corridors.map((c) => (
                <option key={c.route_id} value={c.route_id}>
                  Route {c.route_id} — {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600 }}>Occupancy:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              style={{ fontSize: '12px', padding: '4px 8px' }}
            >
              <option value="all">All Occupancies</option>
              <option value="critical">🔴 Critical Overcrowded (DCR ≥ 1.25x)</option>
              <option value="crowded">🟠 Near Capacity (DCR 1.0 - 1.25x)</option>
              <option value="balanced">🟢 Balanced (DCR 0.70 - 1.0x)</option>
              <option value="surplus">⚪ Surplus / Donors (DCR &lt; 0.70x)</option>
            </select>
          </div>

          {/* Delay Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600 }}>Predicted Delay:</span>
            <select
              value={selectedDelay}
              onChange={(e) => setSelectedDelay(e.target.value)}
              style={{ fontSize: '12px', padding: '4px 8px' }}
            >
              <option value="all">All Delay Ranges</option>
              <option value="severe">🔴 Severe Delay (≥ 15 mins)</option>
              <option value="moderate">🟠 Moderate Delay (5 - 14 mins)</option>
              <option value="on_time">🟢 On Schedule (&lt; 5 mins)</option>
            </select>
          </div>

          {/* Search Box */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '8px', color: 'var(--color-ink-muted)' }} />
            <input
              type="text"
              placeholder="Search bus, route, depot..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '26px', fontSize: '12px', paddingRight: '8px', width: '160px' }}
            />
          </div>
        </div>

        {/* Map Layer Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showCorridors}
              onChange={(e) => setShowCorridors(e.target.checked)}
            />
            <span>GIS Corridors</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showStops}
              onChange={(e) => setShowStops(e.target.checked)}
            />
            <span>Transfer Hubs</span>
          </label>
        </div>
      </div>

      {/* Main Two-Column Layout: Leaflet Map + Live Inspector Panel */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isPanel ? '1fr' : 'minmax(500px, 1fr) 390px',
          gap: '16px',
          height: 'calc(100vh - 210px)',
          minHeight: '560px'
        }}
      >
        {/* Leaflet Map Canvas */}
        <div
          style={{
            position: 'relative',
            borderRadius: 'var(--radius-sm)',
            overflow: 'hidden',
            border: 'var(--border-panel)',
            backgroundColor: '#F1F5F9',
            height: '100%',
            minHeight: '560px'
          }}
        >
          <div ref={mapContainerRef} style={{ width: '100%', height: '100%', minHeight: '560px' }} />

          {/* Map Overlay Legend */}
          <div
            style={{
              position: 'absolute',
              bottom: '16px',
              left: '16px',
              backgroundColor: 'rgba(255, 255, 255, 0.94)',
              backdropFilter: 'blur(4px)',
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              border: 'var(--border-panel)',
              fontSize: '11px',
              zIndex: 800,
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}
          >
            <div style={{ fontWeight: 700, fontSize: '11px', color: 'var(--color-ink)', marginBottom: '2px' }}>
              Passenger Load &amp; Delay Status
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '10px', height: '10px', backgroundColor: '#DC2626', borderRadius: '2px' }} />
              <span>Critical Overcrowded (&ge; 88 pax &bull; &ge; 1.25x)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '10px', height: '10px', backgroundColor: '#D97706', borderRadius: '2px' }} />
              <span>Near Capacity (70&ndash;87 pax &bull; 1.0&ndash;1.24x)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '10px', height: '10px', backgroundColor: '#16A34A', borderRadius: '2px' }} />
              <span>Balanced (49&ndash;69 pax &bull; 0.70&ndash;0.99x)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '10px', height: '10px', backgroundColor: '#64748B', borderRadius: '2px' }} />
              <span>Surplus / Donor Candidate (&lt; 49 pax &bull; &lt; 0.70x)</span>
            </div>
          </div>
        </div>

        {/* Right Inspector & Fleet Stream Panel */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            overflowY: 'auto'
          }}
        >
          {/* Selected Bus Detailed Card */}
          {selectedBus ? (
            <div
              style={{
                backgroundColor: 'var(--color-panel)',
                border: 'var(--border-panel)',
                padding: '16px 18px',
                borderRadius: 'var(--radius-sm)',
                boxShadow: '0 2px 6px rgba(0,0,0,0.04)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-ink-muted)' }}>
                    {selectedBus.depot} &bull; {selectedBus.speed_kmh} km/h
                  </span>
                  <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-ink)' }}>
                    {selectedBus.fleet_no}
                  </h3>
                  <div style={{ fontSize: '12px', color: 'var(--color-ink-muted)', marginTop: '1px' }}>
                    {selectedBus.route_name}
                  </div>
                </div>
                <DcrBadge dcr={selectedBus.dcr} />
              </div>

              {/* Occupancy Progress Gauge */}
              <div style={{ margin: '10px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600 }}>Onboard Passenger Load</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                    {selectedBus.passengers} / {selectedBus.capacity} seats ({Math.round(selectedBus.dcr * 100)}%)
                  </span>
                </div>
                <div style={{ width: '100%', height: '10px', backgroundColor: '#E2E8F0', borderRadius: '5px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.min(100, (selectedBus.passengers / 98) * 100)}%`,
                      height: '100%',
                      backgroundColor:
                        selectedBus.status === 'critical'
                          ? '#DC2626'
                          : selectedBus.status === 'crowded'
                          ? '#D97706'
                          : selectedBus.status === 'balanced'
                          ? '#16A34A'
                          : '#64748B',
                      transition: 'width 0.3s ease'
                    }}
                  />
                </div>
              </div>

              {/* Ex-Ante Predicted Delay & Timetable Module */}
              <div
                style={{
                  backgroundColor: 'var(--color-panel-contrast)',
                  border: 'var(--border-hairline)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 12px',
                  marginBottom: '10px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-ink)' }}>
                    Ex-Ante Predicted Delay (60m)
                  </span>
                  <span
                    style={{
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor:
                        selectedBus.delay_status === 'severe'
                          ? '#FEE2E2'
                          : selectedBus.delay_status === 'moderate'
                          ? '#FEF3C7'
                          : '#DCFCE7',
                      color:
                        selectedBus.delay_status === 'severe'
                          ? '#DC2626'
                          : selectedBus.delay_status === 'moderate'
                          ? '#D97706'
                          : '#16A34A'
                    }}
                  >
                    +{selectedBus.predicted_delay_min} mins ({selectedBus.delay_status.toUpperCase()})
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px', marginBottom: '6px' }}>
                  <div>
                    <span style={{ color: 'var(--color-ink-muted)' }}>Scheduled: </span>
                    <strong style={{ fontFamily: 'var(--font-mono)' }}>{selectedBus.scheduled_time}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--color-ink-muted)' }}>Predicted Arrival: </span>
                    <strong style={{ fontFamily: 'var(--font-mono)', color: selectedBus.predicted_delay_min > 5 ? '#DC2626' : 'var(--color-ink)' }}>
                      {selectedBus.predicted_arrival_time}
                    </strong>
                  </div>
                </div>

                {/* Delay Cause Attribution */}
                <div style={{ fontSize: '10px', color: 'var(--color-ink-muted)', borderTop: '1px solid #E2E8F0', paddingTop: '4px' }}>
                  Root Cause: <strong style={{ color: 'var(--color-ink)' }}>+{selectedBus.departure_cascade_delay_min}m</strong> inbound cascade &bull; <strong style={{ color: 'var(--color-ink)' }}>+{selectedBus.dwell_congestion_delay_min}m</strong> dwell friction ({selectedBus.passengers} pax).
                </div>
              </div>

              {/* Dynamic Commuter PIS Advisory Alert */}
              <div
                style={{
                  backgroundColor: '#FEF9C3',
                  border: '1px solid #FDE047',
                  borderRadius: 'var(--radius-sm)',
                  padding: '8px 10px',
                  marginBottom: '10px',
                  fontSize: '11px'
                }}
              >
                <div style={{ fontWeight: 700, color: '#854D0E', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px' }}>
                  <span>📢</span> Public Information Display (PIS) Advisory
                </div>
                <div style={{ color: '#713F12', lineHeight: 1.35 }}>
                  {selectedBus.passenger_advisory}
                </div>
              </div>

              {/* Boarding vs Alighting Metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '10px' }}>
                <div style={{ backgroundColor: 'var(--color-panel-contrast)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '9px', color: 'var(--color-ink-muted)' }}>Boardings</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                    +{selectedBus.total_boarded} pax
                  </div>
                </div>
                <div style={{ backgroundColor: 'var(--color-panel-contrast)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '9px', color: 'var(--color-ink-muted)' }}>Alightings</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                    -{selectedBus.total_alighted} pax
                  </div>
                </div>
              </div>

              {/* Dispatch Action Recommendation */}
              <div
                style={{
                  borderLeft: `4px solid ${selectedBus.status === 'critical' ? '#DC2626' : '#2563EB'}`,
                  backgroundColor: selectedBus.status === 'critical' ? '#FEF2F2' : '#EFF6FF',
                  padding: '8px 10px',
                  borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                  fontSize: '11px'
                }}
              >
                <div style={{ fontWeight: 700, color: 'var(--color-ink)', marginBottom: '1px' }}>
                  Dispatcher Action
                </div>
                <div style={{ color: 'var(--color-ink)' }}>{selectedBus.recommended_action}</div>
              </div>
            </div>
          ) : (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-ink-muted)' }}>
              Click any bus marker on the map to inspect live passenger load and predicted delay.
            </div>
          )}

          {/* Active Fleet List */}
          <div
            style={{
              backgroundColor: 'var(--color-panel)',
              border: 'var(--border-panel)',
              padding: '12px',
              borderRadius: 'var(--radius-sm)',
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              minHeight: '240px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '12px', fontWeight: 700 }}>
                Tracked fleet stream ({filteredBuses.length})
              </span>
              <span style={{ fontSize: '10px', color: 'var(--color-ink-muted)', fontFamily: 'var(--font-mono)' }}>
                Sorted by load
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', overflowY: 'auto', maxHeight: '280px' }}>
              {filteredBuses
                .slice()
                .sort((a, b) => b.passengers - a.passengers)
                .map((b) => {
                  const isSelected = b.id === selectedBusId;
                  return (
                    <button
                      key={b.id}
                      type="button"
                      onClick={() => handleSelectBus(b)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 8px',
                        backgroundColor: isSelected ? 'var(--color-panel-contrast)' : 'transparent',
                        border: isSelected ? '1px solid var(--color-ink)' : '1px solid transparent',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        textAlign: 'left'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            backgroundColor:
                              b.status === 'critical'
                                ? '#DC2626'
                                : b.status === 'crowded'
                                ? '#D97706'
                                : b.status === 'balanced'
                                ? '#16A34A'
                                : '#64748B'
                          }}
                        />
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                            Rt {b.route} &bull; {b.fleet_no}
                          </div>
                          <div style={{ fontSize: '10px', color: 'var(--color-ink-muted)' }}>
                            {b.depot}
                          </div>
                        </div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                          {b.passengers}p &bull; <span style={{ color: b.predicted_delay_min >= 15 ? '#DC2626' : b.predicted_delay_min >= 5 ? '#D97706' : '#16A34A' }}>+{Math.round(b.predicted_delay_min)}m</span>
                        </div>
                        <div style={{ fontSize: '9px', color: 'var(--color-ink-muted)' }}>
                          {b.dcr}x DCR
                        </div>
                      </div>
                    </button>
                  );
                })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
