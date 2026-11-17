#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
git init -q -b main
git config user.email t@example.com
git config user.name Test
git add -A
git commit -qm 'feat: versión inicial'
git tag v0.2.0
echo '# fix' >> src/demo_cli/__init__.py
git commit -qam 'fix: corrige el redondeo de totales con importes negativos'
echo '# test' >> src/demo_cli/__init__.py
git commit -qam 'test: cubre importes negativos'
