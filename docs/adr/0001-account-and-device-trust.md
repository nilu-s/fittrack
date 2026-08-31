# ADR 0001: browser accounts and device principals are separate

Browser ownership comes only from a verified Google OIDC session containing the
internal account UUID and immutable Google subject. A scale bridge authenticates
only as a registered device and submits raw events; it cannot select an account.
