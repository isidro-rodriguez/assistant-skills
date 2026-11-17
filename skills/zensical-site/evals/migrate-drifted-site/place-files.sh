#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
git init -q -b main
git config user.email t@example.com
git config user.name Test
git remote add origin https://github.com/isidro-rodriguez/tareas-cli.git
git add -A
git commit -qm 'feat: versión inicial'
