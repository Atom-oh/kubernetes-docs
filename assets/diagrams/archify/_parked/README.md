# Parked archify specs (do not apply)

Files here are intentionally excluded from the archify apply/render pipeline
(non-`.json` extension, non-flat location). They are kept only as reference.

- `en-gitops-04-flagger-6.architecture.json.parked` — a string translation of
  `ko-gitops-04-flagger-6` (FluxCD HelmRelease + Flagger Canary workflow).
  The ko and en pages have drifted in diagram indexing: ko `04-flagger.md` has
  anchors 0-8, en has 0-7. `en:1355` (`en-gitops-04-flagger-6.svg`) is the
  Image Automation + Canary Automation pipeline, whose real ko twin is
  `ko-gitops-04-flagger-7` (ko:1143). Wiring this file into en:1355 would put
  a HelmRelease diagram under the Image Automation heading. Leave the en static
  SVG in place; author the en image-automation diagram as its own item paired
  with ko-gitops-04-flagger-7.
