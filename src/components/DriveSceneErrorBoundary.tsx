import React from 'react';

interface State {
  hasError: boolean;
  errorMessage: string;
}

interface Props {
  children: React.ReactNode;
  onFallback?: () => void;
}

export class DriveSceneErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[DriveScene] Render error caught by boundary:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return null; // DriveModeView will handle the fallback via webGlSupported flag
    }
    return this.props.children;
  }
}

