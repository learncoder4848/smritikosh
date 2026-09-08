; JSON tags. No official tags.scm exists upstream; written for smritikosh.
;
; Top-level keys only. The capture sits on the `pair` rather than on the key so
; the chunk carries the value with it, and anchoring to `document > object`
; keeps a deeply nested config from exploding into a chunk per key.

; ── top-level sections ───────────────────────────────────────────────────────

(document
  (object
    (pair
      key: (string
        (string_content) @name)) @definition.section))
