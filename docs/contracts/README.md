# API and device contracts

`openapi.json` is the versioned FastAPI snapshot for browser and device API
contracts. `scale-v2*.json` are raw, credential-free ESP32 payload fixtures. They contain
no account or profile field. With the initial configured ranges, 63 kg and
115 kg are accepted for their separate accounts, while 87 kg is discarded
before persistence. The device response never identifies either account.

The live browser API schema is served as `/openapi.json`. Regenerate the
snapshot with `./scripts/update-openapi` when a contract changes; never edit it
by hand. The contract test rejects drift. Review the generated diff against the
approved specification before deployment.
