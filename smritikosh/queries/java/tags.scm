; Java tags. Derived from tree-sitter/tree-sitter-java queries/tags.scm (MIT).
;
; Definitions only; see python/tags.scm for why @reference.call is left out.

; ── classes ──────────────────────────────────────────────────────────────────

(class_declaration
  name: (identifier) @name) @definition.class

(record_declaration
  name: (identifier) @name) @definition.class

; An annotation type is a class-shaped declaration, so it chunks like one.

(annotation_type_declaration
  name: (identifier) @name) @definition.class

; ── interfaces ───────────────────────────────────────────────────────────────

(interface_declaration
  name: (identifier) @name) @definition.interface

; ── enums ────────────────────────────────────────────────────────────────────

(enum_declaration
  name: (identifier) @name) @definition.enum

(enum_constant
  name: (identifier) @name) @definition.class_constant

; ── constructors ─────────────────────────────────────────────────────────────

(constructor_declaration
  name: (identifier) @name) @definition.class_init

; ── methods ──────────────────────────────────────────────────────────────────

(method_declaration
  name: (identifier) @name) @definition.method

(annotation_type_element_declaration
  name: (identifier) @name) @definition.method

; ── constants ────────────────────────────────────────────────────────────────
; `modifiers` holds `static` and `final` as anonymous tokens, so the pair is
; matched against the modifier text rather than as named children.

(field_declaration
  (modifiers) @_mods
  declarator: (variable_declarator
    name: (identifier) @name)
  (#match? @_mods "static")
  (#match? @_mods "final")) @definition.class_constant
