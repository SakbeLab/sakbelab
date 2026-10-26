"""Backwards-compatible entry point; the implementation lives in socket_console.

python -m sakbe.engines.iol_console <socket>
"""

import sys

from sakbe.engines.socket_console import main

if __name__ == "__main__":
    main(sys.argv[1])
