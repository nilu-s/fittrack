---
name: fittrack-ia-interaction
description: Define FitTrack's information architecture and interaction contracts, especially for the mixed day feed and its specialized meal and training features. Use before changing navigation, entry behavior, sheets, or dialogs.
---

# FitTrack IA and Interaction

Read `docs/design/fittrack-day-feed-interaction.md` before changing a related
surface. Inspect the active route and existing component behavior first.

Keep the mixed day feed, but preserve type-specific behavior:

- To-dos are compact, directly completable entries.
- Meals open a dedicated nutrition workflow.
- Training opens a dedicated workout workflow.
- Biometrics are observations, not to-dos.

Specify task flow, entry states, empty/error/recovery states, mobile and
keyboard paths, and focus behavior. Every important action must have a visible,
native-control path; gestures are optional accelerators.

Do not choose palettes or introduce component implementations. Do not alter
account, sync, API, or health-data semantics.
