'use client';

import { useState, type FormEvent } from 'react';
import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material';
import { useRouter } from 'next/navigation';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from '@/components/LocaleProvider';

export default function LoginPage() {
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { locale } = useLocale();

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey }),
      });

      if (!res.ok) {
        setError(getMessage(locale, 'interaction.loginInvalidApiKey'));
        return;
      }

      const { access_token, expires_in } = await res.json();
      localStorage.setItem('aegis_token', access_token);
      localStorage.setItem('aegis_token_expires', String(Date.now() + expires_in * 1000));
      router.push('/');
    } catch {
      setError(getMessage(locale, 'interaction.loginConnectionFailed'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', p: 2 }}>
      <Paper sx={{ p: 4, maxWidth: 400, width: '100%' }}>
        <Typography variant="h5" gutterBottom>Aegis-Trader</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          {getMessage(locale, 'interaction.loginSubtitle')}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <form onSubmit={handleLogin}>
          <TextField
            fullWidth
            type="password"
            label={getMessage(locale, 'interaction.loginApiKey')}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Button fullWidth variant="contained" type="submit" disabled={loading || !apiKey}>
            {loading ? getMessage(locale, 'interaction.loginAuthenticating') : getMessage(locale, 'interaction.loginButton')}
          </Button>
        </form>
      </Paper>
    </Box>
  );
}
