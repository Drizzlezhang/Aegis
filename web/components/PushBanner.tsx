'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Alert, Snackbar } from '@mui/material';
import { useWebSocket } from '@/hooks/useWebSocket';

interface PushMessage {
  type: 'push';
  event_id: string;
  push_type: string;
  title: string;
  body_markdown: string;
  related_symbols: string[];
  trace_url: string | null;
}

interface ToastItem {
  id: string;
  message: PushMessage;
  timestamp: number;
}

const TOAST_DURATION = 3000;

export default function PushBanner() {
  const router = useRouter();
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [open, setOpen] = useState(false);
  const [currentToast, setCurrentToast] = useState<ToastItem | null>(null);
  const queueRef = useRef<ToastItem[]>([]);

  const handleMessage = useCallback((data: unknown) => {
    const msg = data as PushMessage;
    if (msg.type !== 'push') return;

    const toast: ToastItem = {
      id: msg.event_id,
      message: msg,
      timestamp: Date.now(),
    };

    queueRef.current = [...queueRef.current, toast];
    if (!open) {
      showNext();
    }
  }, [open]);

  const showNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      setOpen(false);
      setCurrentToast(null);
      return;
    }
    const [next, ...rest] = queueRef.current;
    queueRef.current = rest;
    setCurrentToast(next);
    setOpen(true);
  }, []);

  const handleClose = useCallback(() => {
    setOpen(false);
    // Show next after a brief delay
    setTimeout(() => showNext(), 300);
  }, [showNext]);

  const handleClick = useCallback(() => {
    if (currentToast?.message.trace_url) {
      router.push(currentToast.message.trace_url);
    }
    handleClose();
  }, [currentToast, router, handleClose]);

  // Auto-dismiss after TOAST_DURATION
  useEffect(() => {
    if (!open || !currentToast) return;
    const timer = setTimeout(() => {
      handleClose();
    }, TOAST_DURATION);
    return () => clearTimeout(timer);
  }, [open, currentToast, handleClose]);

  const { status } = useWebSocket('/api/push/stream', {
    onMessage: handleMessage,
  });

  if (!currentToast) return null;

  return (
    <Snackbar
      open={open}
      anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      sx={{ mt: 8 }}
    >
      <Alert
        severity="info"
        variant="filled"
        onClose={handleClose}
        onClick={handleClick}
        sx={{
          cursor: currentToast.message.trace_url ? 'pointer' : 'default',
          maxWidth: 480,
          '& .MuiAlert-message': { overflow: 'hidden' },
        }}
      >
        <div>
          <div className="text-xs opacity-70">{currentToast.message.push_type}</div>
          <div className="font-semibold text-sm">{currentToast.message.title}</div>
          {currentToast.message.body_markdown && (
            <div className="text-xs mt-0.5 opacity-80">
              {currentToast.message.body_markdown.replace(/[*_]/g, '')}
            </div>
          )}
        </div>
      </Alert>
    </Snackbar>
  );
}
