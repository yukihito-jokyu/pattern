#!/usr/bin/env bash
# テンプレートのモジュール名を一括置換する。使い方: ./scripts/rename-module.sh github.com/acme/app
set -euo pipefail

new="${1:?usage: rename-module.sh <new module path>}"
old="$(go list -m)"

if [[ "$old" == "$new" ]]; then
  echo "module is already $new"
  exit 0
fi

go mod edit -module "$new"
grep -rlF --exclude-dir=.git --exclude-dir=bin "$old" . | while read -r f; do
  perl -pi -e "s#\Q${old}\E#${new}#g" "$f"
done

echo "renamed: $old -> $new"
