"""Allow ``python -m rqg.cli`` to work."""

import sys

from . import main

sys.exit(main())
