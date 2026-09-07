; Markdown tags. No official tags.scm exists upstream; written for smritikosh.
;
; The capture is placed on `section`, not on the heading, because the chunker
; turns the captured node into the chunk and a bare heading would yield a
; one-line chunk with no content to embed. `section` spans the heading and the
; prose beneath it, which is the unit a reader would actually want back.
;
; Sections nest, so an h2 section is also inside its h1 section. The chunker
; needs to drop captures contained within a higher-priority capture; the same
; rule handles enum bodies in Python.
;
; This grammar only opens a new `section` for an ATX heading. A setext heading
; is a sibling inside whichever section already applies, so the second pattern
; below resolves to the enclosing section: in a mixed document that is a node
; the first pattern already captured, and in an all-setext document it is the
; single document-wide section. Either way the text is indexed; only the
; section boundaries are coarser than the `===` underline suggests.

; ── sections ─────────────────────────────────────────────────────────────────

(section
  (atx_heading
    heading_content: (inline) @name)) @definition.section

(section
  (setext_heading
    heading_content: (paragraph) @name)) @definition.section

; ── fenced code blocks ───────────────────────────────────────────────────────
; Only blocks that declare a language, since an unlabelled fence has no name to
; key on and the extractor drops nameless matches anyway.

(fenced_code_block
  (info_string
    (language) @name)) @definition.code_block
