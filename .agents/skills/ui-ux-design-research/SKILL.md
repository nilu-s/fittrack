---
name: ui-ux-design-research
description: Research implementable UI/UX patterns and component options for an existing product screen, then recommend a focused design direction. Use when design research is requested or the interaction direction is unclear; do not use for already specified UI changes that can be implemented directly.
metadata:
  short-description: Find implementable UI patterns and design references
---

# UI/UX Design Research

Turn a concrete product problem into a decision-ready UI recommendation. Find transferable interaction patterns, not a gallery of attractive screenshots.

## Start with the product context

Before researching, inspect the affected screen and its nearby layout, design tokens, existing components, responsive behavior, dependencies, available UI libraries, validation scripts, and known constraints. Extract:

- product and user context;
- target screen, platform, and breakpoints;
- observed user problem and current interaction model;
- desired visual character;
- technical limits, including framework, reusable components, and whether adding dependencies is justified.

If the context is missing, use a narrow assumption and label it. Do not turn an inspiration request into a full redesign or code change without authorization.

## Research sources and evaluate patterns

Browse for current sources. Use at least two real, comparable products and at least one official component or accessibility source. Prefer sources in this order:

1. Real, live products with the same workflow or information shape.
2. Official documentation for components and accessibility guidance.
3. Established design systems and substantiated UX case studies.
4. Dribbble, Behance, and similar galleries only as visual inspiration, never as usability evidence.

For every source, record the exact pattern worth considering and why it transfers to this product. Reject patterns that conflict with the product's platform, accessibility needs, data density, or implementation scope.

When the task has a concrete interaction problem, compare at least two interaction models. Include keyboard, touch, and screen-reader implications where relevant. Treat drag and drop as an enhancement only when there is an equivalent direct interaction; do not make it the sole workflow.

## Use delegation deliberately

When the user explicitly asks for a subagent, or explicitly permits optional delegation, and delegation is available, use a subagent when it can independently compare multiple interaction models or gather time-sensitive sources in parallel. Delegate a bounded research task with a fixed, short deliverable. State the product context, the problem, non-goals, source priority, and output format.

For bounded source and pattern research, prefer a fast, lower-cost model such as Luna. Escalate to a stronger model only when the delegated task requires synthesising conflicting evidence into a product or design-system architecture decision, or when the research itself is unusually ambiguous. State the chosen model's role in the delegation prompt; do not use a stronger model merely to collect links.

Use this shape, adapting the bracketed details:

```text
Research [target workflow] for [product and users].

Context: [screen, platform, existing visual language, technical stack].
Problems: [specific usability failures].
Non-goals: [what must not expand].
Source priority: real products and official component/accessibility docs first;
inspiration galleries only as a visual supplement.

Return a preliminary evidence checkpoint after the first three strong sources. Use an 8–12 minute deadline unless the parent sets another budget. Return within that budget:
1. Five sources with direct links; for each, name up to two observable patterns.
2. Two or three interaction models with benefits, risks, and accessibility notes.
3. One recommended model for this product and why.
4. A short list of locally buildable components or narrowly justified libraries.
5. The preliminary result if interrupted, with unresearched comparisons marked clearly.

Do not edit files or provide generic visual trends.
```

The primary agent should work on a non-overlapping task while the subagent researches. Wait only when the result blocks synthesis; at the deadline, use the documented preliminary findings and report the limitation rather than inventing results.

## Decide before proposing implementation

Score each viable direction against:

- clarity of the primary task;
- density and scanability on the target screen;
- responsive behavior and visible overflow/scrolling;
- accessibility and input parity: focus order and restoration, visible focus, contrast, target sizes, and a complete non-drag workflow;
- semantic structure, including whether a table, grid, or ordinary grouped list is appropriate;
- consistency with the existing visual language;
- implementation cost and dependency footprint.

Prefer small local components when the product already has a design-token system. Name the existing components and tokens to reuse or extend. Recommend a library only for a complex, repeated behavior such as a searchable combobox, dialog, popover, or keyboard-managed composite control.

## Deliverable

Give a concise, decision-ready result in this order:

1. **Recommendation:** one sentence naming the preferred pattern.
2. **Reference matrix:** source, transferable pattern, benefit, and caveat.
3. **Options compared:** two or three approaches, with why one wins.
4. **Proposed UI structure:** hierarchy, editing flow, responsive adaptation, and visual direction.
5. **Component plan:** existing components to reuse, local components to add, and a library option only where it adds clear value.
6. **First implementation package:** small, reversible changes that can be built and checked next.
7. **Open decisions:** only choices that need product-owner input.

Cite every external claim with a direct link. Separate evidence from inference. Do not claim a source proves usability merely because it looks polished.
