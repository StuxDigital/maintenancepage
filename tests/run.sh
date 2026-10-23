#!/bin/bash
# Maintenance Page - test suite: the version check (tests/version.sh), then the site checks
# (Discord previews, icon set, page heads) with Python's unittest.
# Usage: bash tests/run.sh
# Needs Python 3; the dev-server checks also use PHP 7.4 ($PHP_BIN, php74, php7.4,
# %LOCALAPPDATA%\Programs\PHP\7.4\php.exe or php) and are skipped without it or without .github/dev-router.php.
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
    for candidate in python3 python; do
        if "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 6))' >/dev/null 2>&1; then PY="$candidate"; break; fi
    done
fi
if [ -z "$PY" ]; then
    echo "Python 3 is needed to run the tests." >&2
    exit 1
fi

bash "$DIR/version.sh"
"$PY" -m unittest discover -s "$DIR" -p 'test_*.py' "$@"
