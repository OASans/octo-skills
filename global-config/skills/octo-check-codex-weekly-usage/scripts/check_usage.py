"""Read the weekly Codex allowance through the existing local daemon."""

from datetime import datetime
import math
import os
from pathlib import Path
import sys

# Reuse the repository's Unix WebSocket client without invoking its listener.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / 'tool-codex-capacity-and-quota-listener' / 'scripts'))
from app_server import AppServer, RpcError


def weekly_summary(response):
    buckets = response.get('rateLimitsByLimitId') or {}
    bucket = buckets.get('codex') or response.get('rateLimits')
    if not bucket or bucket.get('limitId') not in (None, 'codex'):
        raise ValueError('No Codex allowance was returned for this account.')
    for field in ('primary', 'secondary'):
        window = bucket.get(field)
        if window and window.get('windowDurationMins') == 7 * 24 * 60:
            break
    else:
        raise ValueError('No weekly Codex allowance was returned for this account.')

    used = window.get('usedPercent')
    if (type(used) not in (int, float) or not math.isfinite(used)
            or not 0 <= used <= 100):
        raise ValueError('The weekly usage percentage is missing or invalid.')
    reset = window.get('resetsAt')
    if reset is None:
        reset_text = 'unavailable'
    elif type(reset) not in (int, float) or not math.isfinite(reset):
        raise ValueError('The weekly reset timestamp is invalid.')
    else:
        reset_text = datetime.fromtimestamp(reset).astimezone().strftime(
            '%Y-%m-%d %H:%M %Z (UTC%z)')
    return (f'Codex weekly allowance: {100 - used:g}% remaining ({used:g}% used).\n'
            f'Resets: {reset_text}.')


def main():
    codex_home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    socket_path = codex_home / 'app-server-control' / 'app-server-control.sock'
    try:
        rpc = AppServer(socket_path)
        try:
            response = rpc.call('account/rateLimits/read', {})
        finally:
            rpc.close()
        print(weekly_summary(response))
    except (OSError, RpcError, ValueError, KeyError, TypeError, OverflowError) as error:
        print(f'Could not check Codex weekly usage: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
