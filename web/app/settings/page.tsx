'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Slider,
  Stack,
  Switch,
  TextField,
  Typography,
  Alert,
  Divider,
} from '@mui/material';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from '@/components/LocaleProvider';
import type { SettingsData } from '@/lib/api';
import { getSettings, updateSettings, testTelegramConnection, getNotificationChannels } from '@/lib/api';

const DEFAULT_SETTINGS: SettingsData = {
  telegram: {
    botToken: '',
    chatId: '',
    enabled: false,
  },
  notifications: {
    highConfidence: true,
    onCompletion: false,
    onError: true,
  },
  confidenceThreshold: 0.7,
  silentHours: {
    start: '22:00',
    end: '08:00',
  },
};

export default function SettingsPage() {
  const { locale } = useLocale();
  const [settings, setSettings] = useState<SettingsData>(DEFAULT_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookHeaders, setWebhookHeaders] = useState('');
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [channels, setChannels] = useState<Array<{ type: string; available: boolean }>>([]);

  useEffect(() => {
    getSettings()
      .then((data) => setSettings(data))
      .catch(() => {
        setMsg({ type: 'warning', text: 'Failed to load settings from server, using defaults' });
      })
      .finally(() => setLoaded(true));
    void getNotificationChannels().then(setChannels).catch(() => {});
  }, []);

  if (!loaded) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  const updateTelegram = (patch: Partial<SettingsData['telegram']>) => {
    setSettings((prev) => ({ ...prev, telegram: { ...prev.telegram, ...patch } }));
  };

  const updateNotifications = (patch: Partial<SettingsData['notifications']>) => {
    setSettings((prev) => ({
      ...prev,
      notifications: { ...prev.notifications, ...patch },
    }));
  };

  const updateSilentHours = (patch: Partial<SettingsData['silentHours']>) => {
    setSettings((prev) => ({
      ...prev,
      silentHours: { ...prev.silentHours, ...patch },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSettings(settings);
      setMsg({ type: 'success', text: getMessage(locale, 'interaction.settingsSaved') });
    } catch {
      setMsg({ type: 'error', text: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestMessage = async () => {
    if (!settings.telegram.botToken || !settings.telegram.chatId) {
      setMsg({ type: 'error', text: getMessage(locale, 'interaction.settingsTestFailed') });
      return;
    }
    setTesting(true);
    try {
      const ok = await testTelegramConnection(settings.telegram.botToken, settings.telegram.chatId);
      if (ok) {
        setMsg({ type: 'success', text: getMessage(locale, 'interaction.settingsTestSent') });
      } else {
        setMsg({ type: 'error', text: getMessage(locale, 'interaction.settingsTestFailed') });
      }
    } catch {
      setMsg({ type: 'error', text: getMessage(locale, 'interaction.settingsTestFailed') });
    } finally {
      setTesting(false);
    }
  };

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <Paper sx={{ p: 3, mb: 3, borderRadius: 3 }} elevation={0} variant="outlined">
      <Typography variant="h6" fontWeight={600} gutterBottom>
        {title}
      </Typography>
      <Divider sx={{ mb: 2 }} />
      {children}
    </Paper>
  );

  return (
    <Box sx={{ p: { xs: 2, lg: 4 }, maxWidth: 700, mx: 'auto' }}>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        {getMessage(locale, 'common.settings')}
      </Typography>

      {msg && (
        <Alert severity={msg.type} onClose={() => setMsg(null)} sx={{ mb: 2 }}>
          {msg.text}
        </Alert>
      )}

      <Section title={getMessage(locale, 'interaction.settingsTelegram')}>
        <Stack spacing={2}>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography>{getMessage(locale, 'interaction.schedulerEnabled')}</Typography>
            <Switch
              checked={settings.telegram.enabled}
              onChange={(e) => updateTelegram({ enabled: e.target.checked })}
            />
          </Stack>
          <TextField
            label={getMessage(locale, 'interaction.settingsBotToken')}
            value={settings.telegram.botToken}
            onChange={(e) => updateTelegram({ botToken: e.target.value })}
            type="password"
            size="small"
            fullWidth
          />
          <TextField
            label={getMessage(locale, 'interaction.settingsChatId')}
            value={settings.telegram.chatId}
            onChange={(e) => updateTelegram({ chatId: e.target.value })}
            size="small"
            fullWidth
          />
          <Button
            variant="outlined"
            onClick={handleTestMessage}
            disabled={testing}
            sx={{ alignSelf: 'flex-start' }}
          >
            {testing ? (
              <CircularProgress size={16} sx={{ mr: 1 }} />
            ) : null}
            {getMessage(locale, 'interaction.settingsTestMessage')}
          </Button>
        </Stack>
      </Section>

      <Section title="Webhook Configuration">
        <Stack spacing={2}>
          <TextField
            label="Webhook URL"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            size="small"
            fullWidth
            placeholder="https://hooks.example.com/notify"
          />
          <TextField
            label="Custom Headers (JSON, optional)"
            value={webhookHeaders}
            onChange={(e) => setWebhookHeaders(e.target.value)}
            size="small"
            fullWidth
            multiline
            rows={2}
            placeholder='{"Authorization": "Bearer xxx"}'
          />
          <Button
            variant="outlined"
            disabled={testingWebhook || !webhookUrl}
            onClick={async () => {
              setTestingWebhook(true);
              try {
                const res = await fetch('/api/notifications/channels');
                if (res.ok) {
                  setMsg({ type: 'success', text: 'Webhook test: channels endpoint reachable' });
                } else {
                  setMsg({ type: 'error', text: 'Webhook test failed' });
                }
              } catch {
                setMsg({ type: 'error', text: 'Webhook test failed' });
              } finally {
                setTestingWebhook(false);
              }
            }}
            sx={{ alignSelf: 'flex-start' }}
          >
            {testingWebhook ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
            Test Webhook
          </Button>
        </Stack>
      </Section>

      <Section title="Notification Channels">
        {channels.length === 0 ? (
          <Typography variant="body2" color="text.secondary">No channels configured</Typography>
        ) : (
          <Stack spacing={1}>
            {channels.map((ch) => (
              <Stack key={ch.type} direction="row" alignItems="center" justifyContent="space-between">
                <Typography variant="body2" fontWeight={600} sx={{ textTransform: 'capitalize' }}>
                  {ch.type}
                </Typography>
                <Chip
                  label={ch.available ? 'Online' : 'Offline'}
                  size="small"
                  color={ch.available ? 'success' : 'error'}
                  variant="filled"
                  sx={{ borderRadius: '999px', fontWeight: 700 }}
                />
              </Stack>
            ))}
          </Stack>
        )}
      </Section>

      <Section title={getMessage(locale, 'interaction.settingsNotifications')}>
        <Stack spacing={1}>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography>{getMessage(locale, 'interaction.settingsHighConfidence')}</Typography>
            <Switch
              checked={settings.notifications.highConfidence}
              onChange={(e) => updateNotifications({ highConfidence: e.target.checked })}
            />
          </Stack>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography>{getMessage(locale, 'interaction.settingsOnCompletion')}</Typography>
            <Switch
              checked={settings.notifications.onCompletion}
              onChange={(e) => updateNotifications({ onCompletion: e.target.checked })}
            />
          </Stack>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography>{getMessage(locale, 'interaction.settingsOnError')}</Typography>
            <Switch
              checked={settings.notifications.onError}
              onChange={(e) => updateNotifications({ onError: e.target.checked })}
            />
          </Stack>
        </Stack>
      </Section>

      <Section title={getMessage(locale, 'interaction.settingsConfidenceThreshold')}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {settings.confidenceThreshold.toFixed(2)}
        </Typography>
        <Slider
          value={settings.confidenceThreshold}
          onChange={(_, v) =>
            setSettings((prev) => ({ ...prev, confidenceThreshold: v as number }))
          }
          min={0}
          max={1}
          step={0.05}
          marks={[
            { value: 0, label: '0' },
            { value: 0.5, label: '0.5' },
            { value: 1, label: '1.0' },
          ]}
          valueLabelDisplay="auto"
        />
      </Section>

      <Section title={getMessage(locale, 'interaction.settingsSilentHours')}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField
            label={getMessage(locale, 'interaction.settingsSilentStart')}
            value={settings.silentHours.start}
            onChange={(e) => updateSilentHours({ start: e.target.value })}
            type="time"
            size="small"
            InputLabelProps={{ shrink: true }}
            sx={{ width: 180 }}
          />
          <TextField
            label={getMessage(locale, 'interaction.settingsSilentEnd')}
            value={settings.silentHours.end}
            onChange={(e) => updateSilentHours({ end: e.target.value })}
            type="time"
            size="small"
            InputLabelProps={{ shrink: true }}
            sx={{ width: 180 }}
          />
        </Stack>
      </Section>

      <Button
        variant="contained"
        onClick={handleSave}
        disabled={saving}
        size="large"
        sx={{ px: 4 }}
      >
        {saving ? (
          <CircularProgress size={20} color="inherit" sx={{ mr: 1 }} />
        ) : null}
        {getMessage(locale, 'interaction.settingsSave')}
      </Button>
    </Box>
  );
}