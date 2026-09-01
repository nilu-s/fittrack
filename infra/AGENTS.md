# Infrastructure area rules

Do not expose secrets, host credentials, or production-only mounts in a local
development path. Keep device ingestion separate from browser-session routing.
Any routing, environment, or deployment change names its rollback and health
verification in the task.

Validate Compose and proxy changes without deploying or changing production
environment variables unless explicitly requested.
