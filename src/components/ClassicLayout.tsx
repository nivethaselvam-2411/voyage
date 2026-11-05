import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { FooterPill } from './FooterPill';
import { fetchControlRoomAlerts } from '../services/api';

export const ClassicLayout: React.FC = () => {
  const [alertCount, setAlertCount] = useState<number>(0);

  useEffect(() => {
    fetchControlRoomAlerts()
      .then((alerts) => setAlertCount(alerts.length))
      .catch(() => setAlertCount(0));
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--color-page)' }}>
      <Navbar alertCount={alertCount} />
      <main style={{ flex: 1 }}>
        <Outlet />
      </main>
      <FooterPill />
    </div>
  );
};

