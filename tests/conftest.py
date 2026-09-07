"""Shared setup for tests that reach the network."""

# Corporate proxies (Zscaler etc.) MITM TLS; certifi doesn't know their CA but the
# OS trust store does. Python 3.13 also verifies strictly, which rejects those CAs.
# Same approach pip ships with. S14 should do this at the CLI entrypoint too.
import truststore

truststore.inject_into_ssl()
