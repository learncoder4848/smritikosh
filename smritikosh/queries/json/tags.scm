; JSON tags. No official tags.scm exists upstream; written for smritikosh.
;
; The capture sits on the `pair` rather than on the key so the chunk carries the
; value with it.
;
; Three nesting levels are captured, but only the shallowest that *fits the
; embedder's window* is chunked -- the section strategy discards an oversized
; capture and descends into the deeper ones contained inside it.  So a small
; config still yields one chunk per top-level key (the deeper captures are
; skipped), while a large one is split along its own key boundaries instead of
; at arbitrary lines.  Depth is therefore chosen by size, not fixed here.
;
; Three levels is what real configs need: in the reference corpus
; `chapters` is 24 KB, `chapters.identity` is still 8.7 KB, and only at the
; third level does `chapters.identity.submit_errors` (874 B) fit a 512-token
; window.  Anything still oversized at depth 3 falls through to line-window
; splitting, which is the correct backstop rather than more query depth.

; ── depth 1: top-level sections ──────────────────────────────────────────────

(document
  (object
    (pair
      key: (string
        (string_content) @name)) @definition.section))

; ── depth 2 ──────────────────────────────────────────────────────────────────

(document
  (object
    (pair
      value: (object
        (pair
          key: (string
            (string_content) @name)) @definition.subsection))))

; ── depth 3 ──────────────────────────────────────────────────────────────────

(document
  (object
    (pair
      value: (object
        (pair
          value: (object
            (pair
              key: (string
                (string_content) @name)) @definition.subsubsection))))))
