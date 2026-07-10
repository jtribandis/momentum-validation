#!/usr/bin/env python3
from pathlib import Path
import argparse
p=argparse.ArgumentParser(); p.add_argument('--module', required=True); args=p.parse_args()
if not Path('config/module_inventory.yaml').exists():
    raise SystemExit(f'{args.module} disabled: config/module_inventory.yaml is missing. CORE validation may proceed without this module.')
print(f'PASS {args.module} module inventory present')
