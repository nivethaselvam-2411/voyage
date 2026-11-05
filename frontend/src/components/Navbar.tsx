import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Bus, Activity } from 'lucide-react';

interface NavbarProps {
  alertCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({ alertCount }) => {
  const navItems = [
    { to: '/control-room', label: 'Control room', badge: alertCount },
    { to: '/depots', label: 'Depots' },
    { to: '/fleet', label: 'Fleet' },
    { to: '/scorecard', label: 'Scorecard' },
    { to: '/dataset', label: 'Judge dataset', tag: 'Theme 4' }
  ];

  return (
    <header
      style={{
        backgroundColor: 'var(--color-panel)',
        borderBottom: 'var(--border-panel)',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}
    >
      <div
        style={{
          maxWidth: '1440px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: '56px',
          gap: '16px'
        }}
      >
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Link
            to="/control-room"
            style={{
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'baseline',
              gap: '8px'
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-serif)',
                fontSize: '22px',
                color: 'var(--color-ink)',
                letterSpacing: '-0.01em'
              }}
            >
              Marina Sentinel
            </span>
            <span
              style={{
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                color: 'var(--color-accent-orange)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}
            >
              MTC Chennai
            </span>
          </Link>
          <span
            style={{
              display: 'none',
              fontSize: '12px',
              color: 'var(--color-ink-muted)',
              borderLeft: '1px solid #DFD5BD',
              paddingLeft: '12px'
            }}
            className="navbar-subtitle"
          >
            60-minute corridor overcrowding copilot
          </span>
        </div>

        {/* Navigation links */}
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            height: '100%'
          }}
          aria-label="Main navigation"
        >
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 500,
                textDecoration: 'none',
                color: isActive ? 'var(--color-ink)' : 'var(--color-ink-muted)',
                backgroundColor: isActive ? 'var(--color-panel-contrast)' : 'transparent',
                borderRadius: 'var(--radius-sm)',
                transition: 'background-color var(--transition-speed) ease'
              })}
            >
              <span>{item.label}</span>
              {'tag' in item && item.tag && (
                <span
                  style={{
                    backgroundColor: 'var(--color-cream)',
                    border: 'var(--border-hairline)',
                    color: 'var(--color-accent-orange)',
                    fontSize: '9px',
                    fontFamily: 'var(--font-mono)',
                    padding: '1px 4px',
                    borderRadius: 'var(--radius-sm)',
                    fontWeight: 700,
                    textTransform: 'uppercase'
                  }}
                >
                  {item.tag}
                </span>
              )}
              {typeof item.badge === 'number' && item.badge > 0 && (
                <span
                  style={{
                    backgroundColor: 'var(--dcr-red)',
                    color: '#FFFFFF',
                    fontSize: '10px',
                    fontFamily: 'var(--font-mono)',
                    padding: '1px 5px',
                    borderRadius: 'var(--radius-sm)',
                    fontWeight: 700
                  }}
                >
                  {item.badge}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Right side tools: Drive mode button & Telemetry indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-ink-muted)',
              backgroundColor: 'var(--color-panel-light)',
              padding: '4px 8px',
              border: 'var(--border-panel)',
              borderRadius: 'var(--radius-sm)'
            }}
          >
            <Activity size={12} style={{ color: 'var(--dcr-green)' }} />
            <span>ETM Stream Online</span>
          </div>

          <Link
            to="/drive"
            style={{
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              backgroundColor: 'var(--color-accent-orange)',
              color: '#FFFFFF',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              transition: 'background-color var(--transition-speed) ease'
            }}
            title="Switch to 3D Drive Mode"
          >
            <Bus size={14} />
            <span>Drive mode</span>
          </Link>
        </div>
      </div>
    </header>
  );
};
