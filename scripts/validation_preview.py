"""Launch the existing validation workspace without changing its database profile."""
from dataclasses import replace
from pathlib import Path
import argparse
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('server', choices=['api', 'web'])
parser.add_argument('--mode', choices=['preview', 'demo'], default='preview')
parser.add_argument('--api-port', type=int, default=8008)
parser.add_argument('--web-port', type=int, default=3008)
args = parser.parse_args()
if args.server == 'web':
    env = dict(os.environ, AEGIS_API=f'http://127.0.0.1:{args.api_port}')
    subprocess.run(['node', str(root/'frontend/node_modules/next/dist/bin/next'),
                    'start', '--hostname', '127.0.0.1', '--port', str(args.web_port)],
                   cwd=root/'frontend', env=env, check=True)
else:
    import uvicorn
    sys.path.insert(0, str(root/'backend'))
    from aegis_v2.api import create_app
    origin = f'http://127.0.0.1:{args.web_port}'
    runtime = root/'.runtime'/f'english-{args.mode}-{args.api_port}'
    if args.mode == 'demo':
        from aegis_v2.demo import build_platform, seed
        platform = build_platform(runtime_dir=runtime)
        platform.settings = replace(platform.settings, allowed_origins=(origin,))
        seed(platform)
        app = create_app(platform.settings, platform=platform)
    else:
        from aegis_v2.config import Settings
        cfg = replace(Settings.load(), database_url='sqlite:///'+str(runtime/'audit.db'),
                      runtime_dir=runtime, allowed_origins=(origin,))
        app = create_app(cfg, start_workers=True)
    uvicorn.run(app, host='127.0.0.1', port=args.api_port)
