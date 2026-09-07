; Kotlin tags. Derived from fwcd/tree-sitter-kotlin queries/tags.scm (MIT).
;
; Definitions only; see python/tags.scm for why @reference.call is left out.
;
; This grammar uses positional children rather than named fields, so patterns
; match `(type_identifier)` and `(simple_identifier)` by position. Interfaces
; and enums are both class_declaration: an interface is distinguished by the
; anonymous `interface` token, an enum by carrying an enum_class_body.

; ── enums ────────────────────────────────────────────────────────────────────
; Overlaps @definition.class below, as in Python; CAPTURE_PRIORITY resolves it.

(class_declaration
  (type_identifier) @name
  (enum_class_body)) @definition.enum

(enum_entry
  (simple_identifier) @name) @definition.class_constant

; ── interfaces ───────────────────────────────────────────────────────────────

(class_declaration
  "interface"
  (type_identifier) @name) @definition.interface

; ── classes and objects ──────────────────────────────────────────────────────

(class_declaration
  (type_identifier) @name) @definition.class

(object_declaration
  (type_identifier) @name) @definition.class

; ── constructors ─────────────────────────────────────────────────────────────
; Neither constructor form carries its own name, so the enclosing class name is
; captured as @name; the extractor drops any match without one.

(class_declaration
  (type_identifier) @name
  (primary_constructor) @definition.class_init)

(class_declaration
  (type_identifier) @name
  (class_body
    (secondary_constructor) @definition.class_init))

; ── type aliases ─────────────────────────────────────────────────────────────

(type_alias
  (type_identifier) @name) @definition.type

; ── functions and methods ────────────────────────────────────────────────────
; function_declaration serves both, so the two are told apart by position.

(source_file
  (function_declaration
    (simple_identifier) @name) @definition.function)

(class_body
  (function_declaration
    (simple_identifier) @name) @definition.method)

; ── constants ────────────────────────────────────────────────────────────────

(source_file
  (property_declaration
    (variable_declaration
      (simple_identifier) @name)
    (#match? @name "^[A-Z][A-Z0-9_]*$")) @definition.constant)

(class_body
  (property_declaration
    (variable_declaration
      (simple_identifier) @name)
    (#match? @name "^[A-Z][A-Z0-9_]*$")) @definition.class_constant)
