import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ClassicLayout } from './components/ClassicLayout';
import { ControlRoomView } from './views/ControlRoomView';
import { LiveMapView } from './views/LiveMapView';
import { DepotsView } from './views/DepotsView';
import { FleetView } from './views/FleetView';
import { ScorecardView } from './views/ScorecardView';
import { DatasetView } from './views/DatasetView';
import { DriveModeView } from './views/DriveMode/DriveModeView';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Classic Dashboard Screens (default landing) */}
        <Route element={<ClassicLayout />}>
          <Route path="/" element={<Navigate to="/control-room" replace />} />
          <Route path="/control-room" element={<ControlRoomView />} />
          <Route path="/live-map" element={<LiveMapView />} />
          <Route path="/depots" element={<DepotsView />} />
          <Route path="/fleet" element={<FleetView />} />
          <Route path="/scorecard" element={<ScorecardView />} />
          <Route path="/dataset" element={<DatasetView />} />
        </Route>

        {/* Drive Mode — accessible via the Navbar "Drive mode" button */}
        <Route path="/drive" element={<DriveModeView />} />

        {/* Fallback to Control Room */}
        <Route path="*" element={<Navigate to="/control-room" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
