'use client';

import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { Box, Button, Typography } from '@mui/material';
import { getMessage } from '@/i18n/get-message';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h5" gutterBottom>
            {getMessage('zh-CN', 'interaction.errorBoundaryTitle')}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            {this.state.error?.message || getMessage('zh-CN', 'interaction.errorBoundaryMessage')}
          </Typography>
          <Button
            variant="contained"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            {getMessage('zh-CN', 'interaction.errorBoundaryRetry')}
          </Button>
        </Box>
      );
    }

    return this.props.children;
  }
}
