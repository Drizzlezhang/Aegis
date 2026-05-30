'use client';

import { useCallback, useRef, useState } from 'react';
import { useWebSocket, type WebSocketStatus } from '@/hooks/useWebSocket';

interface PhaseData {
  type: 'phase';
  symbol: string;
  phase: string;
  confidence: number;
  composite_score: number;
  transition: string | null;
  timestamp: string;
}

interface UsePhaseStreamReturn {
  status: WebSocketStatus;
  currentPhase: PhaseData | null;
  phaseHistory: PhaseData[];
  setSymbol: (symbol: string) => void;
}

export function usePhaseStream(initialSymbol?: string): UsePhaseStreamReturn {
  const [symbol, setSymbol] = useState(initialSymbol ?? '');
  const [currentPhase, setCurrentPhase] = useState<PhaseData | null>(null);
  const historyRef = useRef<PhaseData[]>([]);

  const url = symbol ? `/ws/phase?symbol=${encodeURIComponent(symbol)}` : null;

  const onMessage = useCallback((data: PhaseData) => {
    if (data.type === 'phase') {
      setCurrentPhase(data);
      historyRef.current = [data, ...historyRef.current].slice(0, 50);
    }
  }, []);

  const { status } = useWebSocket(url, { onMessage });

  return {
    status,
    currentPhase,
    phaseHistory: historyRef.current,
    setSymbol,
  };
}
