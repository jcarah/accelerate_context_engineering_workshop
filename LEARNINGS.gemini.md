# Learnings and Troubleshooting

## CopilotKit Integration
- **Issue:** "LangGraphHttpAgent import from @copilotkit/runtime is deprecated."
- **Fix:** Import `LangGraphHttpAgent` from `@copilotkit/runtime/langgraph` instead of `@copilotkit/runtime`.
- **Context:** Occurred in `app/api/copilotkit/route.ts` when using `@copilotkit/runtime` version `0.33+`.

- **Issue:** "Module not found: Can't resolve '@/lib/summaryHelpers'" in Frontend.
- **Fix:** Recreated missing `app/frontend/lib` directory with `types.ts`, `summaryHelpers.ts`, and `parseCodeBlocks.ts`.
- **Context:** Essential utility files were missing from the project structure.

- **Issue:** "Agent 'retail_location_strategy' not found" runtime error.
- **Fix:** Ensure `route.ts` compiles correctly (fix deprecation) and `app_name` in backend matches `agents` key in `route.ts` and `useCoAgent` name in `page.tsx`.

## Dependency Management
- **Warning:** Do NOT run `npm audit fix --force` blindly on this project. It downgrades `@copilotkit/react-ui` to version `0.2.0`, breaking the UI.
- **Protocol:** Stick to explicit version installs for CopilotKit (e.g., `1.50.1`).
