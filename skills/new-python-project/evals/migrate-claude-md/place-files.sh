#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
git init -q -b main
git config user.email t@example.com
git config user.name Test
git add -A
git commit -qm "chore: estado inicial"
