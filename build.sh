#!/usr/bin/env bash
set -euo pipefail

PYTHON27="${PYTHON27:-$(pyenv prefix 2.7.18 2>/dev/null)/bin/python2.7}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(sed -n 's:.*<version>\(.*\)</version>.*:\1:p' "$ROOT/src/meta.xml")"
ID="$(sed -n 's:.*<id>\(.*\)</id>.*:\1:p' "$ROOT/src/meta.xml")"
STAGE="$ROOT/build/stage"
OUT="$ROOT/dist/${ID}_${VERSION}.wotmod"

rm -rf "$ROOT/build" && mkdir -p "$STAGE" "$ROOT/dist"
cp "$ROOT/src/meta.xml" "$STAGE/"
(cd "$ROOT/src" && find res -name '*.py' | while read -r f; do
    mkdir -p "$STAGE/$(dirname "$f")"
    "$PYTHON27" -c 'import py_compile, sys; py_compile.compile(sys.argv[1], sys.argv[2], sys.argv[3], doraise=True)' \
        "$f" "$STAGE/${f%.py}.pyc" "${f}"
done)
(cd "$ROOT/src" && find res -type f ! -name '*.py' ! -name '*.pyc' ! -path '*/__pycache__/*' | while read -r f; do
    mkdir -p "$STAGE/$(dirname "$f")"
    cp "$f" "$STAGE/$f"
done)

rm -f "$OUT"
# The game reads .wotmod archives only when stored uncompressed, with directory entries and no extra fields.
(cd "$STAGE" && find . -mindepth 1 | sed 's:^\./::' | sort | zip -q -0 -X "$OUT" -@)
echo "$OUT"
