# Cronicl: Pictogramicl-Delivery

**Status:** revised by product direction 2026-09-17
**Owner:** Cronicl household

Pictogramicl is the sole owner of pictogram generation, validation, releases
and initial placeholders. Cronicl neither creates nor accepts SVGs, recipes,
visual overrides, generator jobs or maintainer publication flows.

For a shopping tile the browser requests Cronicl's account-scoped item asset
route. Cronicl validates access, sends only a short public-safe term to
Pictogramicl, and never exposes the Pictogramicl key to a browser. Contact
details, URLs, notes and unsafe/free private values are not forwarded. Such
values use Pictogramicl's `_` initial placeholder.

Cronicl caches SVG bytes under an HMAC of the normalized public term, never
under the original title. Cached metadata is limited to service concept,
revision, ETag, placeholder metadata and retry time. Available revisions are
immutable. Pending/unavailable answers retain Pictogramicl's initial SVG and
are retried only after the service `retry_after` value (15 minutes by default).
The browser may revalidate its private Cronicl asset once per minute.

| Commitment | Verification |
| --- | --- |
| Browser never receives service credentials; item access stays account/space scoped | shopping route tests |
| Cache contains no raw item title and only accepts same-origin service assets | `backend/tests/test_pictogramicl.py` |
| Missing/pending artwork uses Pictogramicl's immutable initial SVG | `backend/tests/test_pictogramicl.py` |
