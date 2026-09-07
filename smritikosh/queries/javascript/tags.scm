; JavaScript tags. Derived from tree-sitter/tree-sitter-javascript queries/tags.scm
; (MIT), which is comprehensive for definitions but has no constructor or
; constant handling.
;
; Definitions only; see python/tags.scm for why @reference.call is left out.

; ── classes ──────────────────────────────────────────────────────────────────

(class_declaration
  name: (identifier) @name) @definition.class

; ── functions ────────────────────────────────────────────────────────────────
; One pattern covers sync and async: `async` is an optional token inside
; function_declaration.

(function_declaration
  name: (identifier) @name) @definition.function

(generator_function_declaration
  name: (identifier) @name) @definition.function

(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: [
      (arrow_function)
      (function_expression)
    ])) @definition.function

; ── constructors ─────────────────────────────────────────────────────────────

(method_definition
  name: (property_identifier) @name
  (#eq? @name "constructor")) @definition.class_init

; ── methods ──────────────────────────────────────────────────────────────────

(method_definition
  name: (property_identifier) @name
  (#not-eq? @name "constructor")) @definition.method

; ── constants ────────────────────────────────────────────────────────────────
; Value types are listed explicitly so a `const HANDLER = () => {}` stays a
; function rather than becoming a constant.

(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: [
      (number)
      (string)
      (template_string)
      (true)
      (false)
      (object)
      (array)
      (call_expression)
    ]
    (#match? @name "^[A-Z][A-Z0-9_]*$"))) @definition.constant

(variable_declaration
  (variable_declarator
    name: (identifier) @name
    value: [
      (number)
      (string)
      (template_string)
      (true)
      (false)
      (object)
      (array)
      (call_expression)
    ]
    (#match? @name "^[A-Z][A-Z0-9_]*$"))) @definition.constant

(field_definition
  property: (property_identifier) @name
  (#match? @name "^[A-Z][A-Z0-9_]*$")) @definition.class_constant
