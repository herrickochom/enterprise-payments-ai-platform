"""Allow ``python -m epap_ingestion`` to invoke the CLI."""
from epap_ingestion.cli import main

raise SystemExit(main())
