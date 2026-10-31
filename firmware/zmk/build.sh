#!/usr/bin/env bash
# Local ZMK build in Docker, same matrix as CI (build.yaml).
#   ./build.sh                     build every entry
#   ./build.sh sage60_left ...     build only these artifact-names
#   ./build.sh --update ...        re-run `west update` first (after editing west.yml)
# The west workspace (zephyr, zmk, modules) and build dirs live in the Docker
# volume "sage60-zmk"; only config/ is mounted from here. UF2s land in out/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
update=0
[ "${1:-}" = --update ] && { update=1; shift; }

docker run --rm -i \
  -v sage60-zmk:/ws \
  -v "$PWD/config:/ws/config:ro" \
  -v "$PWD/build.yaml:/ws/build.yaml:ro" \
  -v "$PWD/out:/out" \
  -e UPDATE=$update \
  -w /ws \
  zmkfirmware/zmk-build-arm:stable \
  python3 - "$@" <<'EOF'
import os, shlex, subprocess, sys, yaml
def sh(cmd): subprocess.run(cmd, shell=True, check=True)
if not os.path.isdir('.west'):
    sh('west init -l config')
if not os.path.isdir('zmk') or os.environ['UPDATE'] == '1':
    sh('west update --fetch-opt=--filter=tree:0')
sh('west zephyr-export >/dev/null')  # registers Zephyr in ~/.cmake, which --rm discards
want = set(sys.argv[1:])
jobs = [j for j in yaml.safe_load(open('build.yaml'))['include']
        if not want or j['artifact-name'] in want]
if want - {j['artifact-name'] for j in jobs}:
    sys.exit(f"unknown artifact-name: {want - {j['artifact-name'] for j in jobs}}")
for j in jobs:
    name = j['artifact-name']
    cmd = ['west', 'build', '-p', 'auto', '-s', 'zmk/app', '-d', f'build/{name}', '-b', j['board']]
    if j.get('snippet'): cmd += ['-S', j['snippet']]
    cmd += ['--', '-DZMK_CONFIG=/ws/config', f"-DSHIELD={j['shield']}"] + shlex.split(j.get('cmake-args', ''))
    print('==>', name, flush=True)
    subprocess.run(cmd, check=True)
    sh(f'cp build/{name}/zephyr/zmk.uf2 /out/{name}.uf2')
EOF
ls -1 out/*.uf2
