---
name: creative-auto-designer
description: Automatically create distinctive, polished frontend designs from rough ideas, vague briefs, screenshots, or existing routes. Use for creative UI direction, landing pages, dashboards, app screens, redesigns, visual polish, responsive frontend implementation, and concept-first web prototypes. Do not use for backend-only work.
---

# Creative Auto Designer

Use this skill when the user asks for creative frontend design, automatic UI generation, visual polish, landing pages, dashboards, app screens, redesigns, or turning a rough idea into a distinctive interface.

The goal is not to produce a generic generated UI. The goal is to create a strong visual concept, implement it in the existing codebase, and verify that it works responsively.

## Default behavior

When the request is underspecified, make reasonable design choices instead of blocking on clarification. Ask a question only when a missing constraint would make the result unsafe, impossible, or likely unusable.

Prefer a finished implementation over a long design explanation. If the user asks for concepts only, provide concepts. Otherwise, design and build.

## Workflow

1. Understand the product
   - Identify the product type, target user, primary action, brand mood, and the one thing the first screen must communicate.
   - If the product is unclear, infer a plausible direction from the app name, route, copy, package, and existing UI.
   - Define a one-sentence visual thesis before coding.

2. Scan the existing frontend
   - Inspect the project structure, framework, routes, component library, styling method, design tokens, Tailwind config, CSS variables, fonts, icons, and existing reusable components.
   - Reuse the project’s existing patterns whenever possible.
   - Do not create a parallel design system unless the project has no usable UI foundation.

3. Generate creative directions internally
   - Consider at least three distinct visual directions before choosing one.
   - Choose the direction that best supports the product’s goal, not the flashiest direction.
   - Favor distinctive composition, strong hierarchy, meaningful empty space, confident typography, and one memorable visual anchor.

4. Design the screen or flow
   - Start with the primary user journey and the first screen.
   - Give every section one job.
   - Make the page understandable by scanning headings and primary actions only.
   - Use contrast, rhythm, proximity, and alignment before decorative effects.
   - Use motion only when it improves hierarchy, feedback, or atmosphere.
   - Add delight through useful details: hover states, focus states, empty states, loading states, microcopy, illustrations, data presentation, and interaction feedback.

5. Implement carefully
   - Use the existing framework and conventions.
   - Keep components small and composable.
   - Use semantic HTML and accessible controls.
   - Preserve existing data flows and APIs unless the user explicitly asks to change them.
   - Avoid breaking unrelated routes or components.
   - Make the design responsive across mobile, tablet, and desktop.

6. Verify visually
   - Run the app using the repository’s normal scripts.
   - If Playwright or browser tooling is available, open the route, inspect the result, resize the viewport, and iterate.
   - Check desktop and mobile.
   - Fix obvious spacing, overflow, contrast, alignment, and interaction issues before reporting completion.

## Creativity principles

Use these principles to avoid generic UI:

- One strong visual anchor beats many decorative elements.
- One accent color is usually stronger than a rainbow palette.
- Custom layout rhythm beats a wall of identical cards.
- A clear story beats a collection of sections.
- Specific copy beats placeholder marketing language.
- Purposeful motion beats constant animation.
- Premium design should still work if shadows, blur, and gradients are removed.

## Avoid these failures

- Generic SaaS hero with vague headline, gradient blob, and card grid.
- Random glassmorphism, neon, or 3D effects with no product reason.
- Repeating the same card layout in every section.
- Busy imagery behind important text.
- Low-contrast text.
- Decorative animation that harms readability.
- Invented brand colors that conflict with an existing design system.
- Replacing real app behavior with static mockups unless the user asks for a prototype only.

## Creative modes

Choose one mode automatically unless the user gives a style:

- Premium minimal: editorial spacing, strong typography, restrained palette, high polish.
- Bold startup: confident hero, energetic hierarchy, sharp sections, memorable CTA.
- Futuristic product: layered depth, technical atmosphere, precise motion, strong dashboard surfaces.
- Warm human: soft structure, friendly copy, approachable colors, clear onboarding.
- Data-rich pro: dense but readable dashboards, strong tables, charts, filters, and status states.
- Playful experimental: surprising layout, expressive visuals, delightful interactions, still usable.

## Output format

When finished, report:

- The chosen visual direction in one sentence.
- Key files changed.
- How you verified the result.
- Any assumptions made.

Keep the final response concise. Do not include a long design essay unless the user asks for one.
