'use client';

import { Button, ButtonGroup } from '@mui/material';
import { useLocale } from './LocaleProvider';

export default function LocaleSwitcher() {
  const { locale, setLocale } = useLocale();

  return (
    <ButtonGroup
      size="small"
      variant="outlined"
      aria-label="locale switcher"
      sx={{
        borderRadius: '999px',
        bgcolor: 'background.paper',
        '& .MuiButton-root': {
          borderColor: 'divider',
          minWidth: 0,
          px: 1.5,
          py: 0.5,
          fontSize: 12,
          fontWeight: 700,
        },
      }}
    >
      <Button
        type="button"
        aria-pressed={locale === 'zh-CN'}
        variant={locale === 'zh-CN' ? 'contained' : 'outlined'}
        onClick={() => setLocale('zh-CN')}
      >
        中文
      </Button>
      <Button
        type="button"
        aria-pressed={locale === 'en'}
        variant={locale === 'en' ? 'contained' : 'outlined'}
        onClick={() => setLocale('en')}
      >
        English
      </Button>
    </ButtonGroup>
  );
}
