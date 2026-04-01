---
description: How to pick up and implement any phase from the PROMPT
---

# Implement a Phase

## Steps

1. Open `CONTINUITY.md` and check the **Phase Checklist** (section 4) to find the next unchecked phase.

2. Open `PROMPT.md` and navigate to the phase section. Each step contains:
   - **File path** — which file to implement
   - **What to do** — specific requirements
   - **Key considerations** — pitfalls and design notes
   - **Testing** — how to verify your work

3. For each step in the phase:
   a. Open the stub file (already created with TODO markers)
   b. Read the module docstring for context
   c. Implement the TODO sections
   d. Follow the testing instructions in PROMPT.md

4. After implementing, wire it into the Flask app:
   - Open `src/backend/create_flask_application.py`
   - Uncomment the relevant blueprint import and registration

5. Rebuild and test:
```bash
docker-compose build backend
docker-compose up -d backend
docker-compose logs -f backend
```

6. Update the Phase Checklist in `CONTINUITY.md`:
   - Mark completed items with `[x]`
   - Note any issues or deviations

## Phase Dependencies

```
Phase 1 (Foundation) → Phase 2 (Telegram) → Phase 3 (OCR)
                                                   ↓
                                    Phase 4 / Phase 5 / Phase 6 (parallel)
                                                   ↓
                                            Phase 7 (Home Assistant)
                                                   ↓
                                            Phase 8 (Backup)
                                                   ↓
                                            Phase 9 (Testing)
```

> **Phases 4, 5, and 6 can be built in any order or in parallel.**
> Phase 2 can be deferred — use stub upload (Step 5) for OCR testing.

## Tips
- Each stub file already has the correct imports and function signatures
- TODO comments show exactly what to implement
- Run tests after each step, not just at the end
- Commit after each completed step
