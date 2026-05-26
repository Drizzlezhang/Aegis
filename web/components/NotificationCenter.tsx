'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import NotificationsRoundedIcon from '@mui/icons-material/NotificationsRounded';
import {
  Badge,
  Box,
  Button,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  Popover,
  Stack,
  Typography,
} from '@mui/material';
import { getNotifications, markAllNotificationsRead, markNotificationRead, type NotificationItem } from '@/lib/api';

const LEVEL_COLORS: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  critical: 'error',
  error: 'error',
  warning: 'warning',
  info: 'info',
};

const CATEGORY_LABELS: Record<string, string> = {
  analysis: 'Analysis',
  position: 'Position',
  system: 'System',
  tracking: 'Tracking',
};

export default function NotificationCenter() {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await getNotifications(50);
      setNotifications(data.notifications);
      setUnreadCount(data.unreadCount);
    } catch {
      // keep existing data on failure
    }
  }, []);

  useEffect(() => {
    void fetchNotifications();
    timerRef.current = setInterval(() => {
      void fetchNotifications();
    }, 30000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchNotifications]);

  const handleOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleMarkRead = async (id: string) => {
    await markNotificationRead(id);
    void fetchNotifications();
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead();
    void fetchNotifications();
  };

  const open = Boolean(anchorEl);

  return (
    <>
      <IconButton onClick={handleOpen} sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
        <Badge badgeContent={unreadCount} color="error">
          <NotificationsRoundedIcon />
        </Badge>
      </IconButton>

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        slotProps={{ paper: { sx: { width: 400, maxHeight: 480 } } }}
      >
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle2" fontWeight={700}>
              Notifications
            </Typography>
            {unreadCount > 0 && (
              <Button size="small" onClick={handleMarkAllRead}>
                Mark all read
              </Button>
            )}
          </Stack>
        </Box>

        {notifications.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No notifications
            </Typography>
          </Box>
        ) : (
          <List disablePadding sx={{ overflow: 'auto', maxHeight: 400 }}>
            {notifications.map((item) => (
              <ListItem key={item.id} disablePadding>
                <ListItemButton
                  onClick={() => handleMarkRead(item.id)}
                  sx={{
                    opacity: item.read ? 0.6 : 1,
                    borderLeft: item.read ? 'none' : '3px solid',
                    borderColor: item.read ? 'transparent' : 'primary.main',
                  }}
                >
                  <Stack spacing={0.5} sx={{ width: '100%' }}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip
                        label={item.level}
                        size="small"
                        color={LEVEL_COLORS[item.level] ?? 'default'}
                        variant="filled"
                        sx={{ textTransform: 'capitalize', borderRadius: '999px', fontWeight: 700, fontSize: '0.65rem' }}
                      />
                      <Chip
                        label={CATEGORY_LABELS[item.category] ?? item.category}
                        size="small"
                        variant="outlined"
                        sx={{ borderRadius: '999px', fontSize: '0.65rem' }}
                      />
                    </Stack>
                    <Typography variant="body2" fontWeight={item.read ? 400 : 700}>
                      {item.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" noWrap>
                      {item.message}
                    </Typography>
                    <Typography variant="caption" color="text.disabled">
                      {new Date(item.createdAt).toLocaleString()}
                    </Typography>
                  </Stack>
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </Popover>
    </>
  );
}
