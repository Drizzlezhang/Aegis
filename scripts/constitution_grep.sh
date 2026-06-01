#!/usr/bin/env bash
# Constitution grep guard — L1/L2/L3 checks
# Violations block merge (GA gate)
set -euo pipefail

# L1: banned words in production code (src/ + web/ only; tests may reference for guard verification)
L1_BANNED='submit_order|place_order|modify_order|cancel_order|PaperBroker'
if grep -rEn "$L1_BANNED" src/ web/ --include='*.py' --include='*.ts' --include='*.tsx' 2>/dev/null; then
    echo "❌ L1 violation: banned words found"; exit 1
fi

# L2: broker path restriction (prevent "wrapping" bypass)
for verb in submit_order place_order modify_order cancel_order; do
    if grep -rEn "$verb" src/agents/strategy_exec/brokers/ src/brokers/ --include='*.py' 2>/dev/null; then
        echo "❌ L2 violation: $verb in broker path"; exit 1
    fi
done

# L3: forbidden Web UI text
L3_BANNED='一键下单|一键跟单|自动执行'
if grep -rEn "$L3_BANNED" web/ --include='*.ts' --include='*.tsx' --include='*.json' 2>/dev/null; then
    echo "❌ L3 violation: forbidden UI text"; exit 1
fi

echo "✅ Constitution grep passed (L1+L2+L3)"
