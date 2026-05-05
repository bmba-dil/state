#!/usr/bin/env bash
# Install @state/opencode-plugin into opencode's plugin directory
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="${SCRIPT_DIR}"

OPECODE_CONFIG="${HOME}/.config/opencode/opencode.json"

if [ ! -f "$OPECODE_CONFIG" ]; then
  echo "Error: opencode config not found at $OPECODE_CONFIG"
  exit 1
fi

echo "@state/opencode-plugin installer"
echo "Plugin path: ${PLUGIN_DIR}"
echo ""

NEEDS_INSTALL=$(python3 -c "
import json, sys
with open('$OPECODE_CONFIG') as f:
    cfg = json.load(f)
plugins = cfg.get('plugin', [])
plugin_path = '$PLUGIN_DIR/src/index.ts'
if plugin_path in plugins:
    print('false')
else:
    print('true')
" 2>/dev/null || echo "true")

if [ "$NEEDS_INSTALL" = "true" ]; then
  echo "Adding plugin to opencode config..."
  python3 -c "
import json, sys
with open('$OPECODE_CONFIG') as f:
    cfg = json.load(f)
plugins = cfg.get('plugin', [])
plugin_path = '$PLUGIN_DIR/src/index.ts'
if plugin_path not in plugins:
    plugins.append(plugin_path)
    cfg['plugin'] = plugins
with open('$OPECODE_CONFIG', 'w') as f:
    json.dump(cfg, f, indent=2)
print('Plugin registered.')
" || {
    echo "Failed to update opencode config."
    echo "Add the following to ${OPECODE_CONFIG} manually:"
    echo '  "plugin": ["'"${PLUGIN_DIR}"'/src/index.ts"]'
    exit 1
  }
else
  echo "Plugin already registered in opencode config."
fi

echo ""
echo "Plugin installed. Restart opencode to load hooks."
echo "Verify with: STATE_MODE=build opencode"
