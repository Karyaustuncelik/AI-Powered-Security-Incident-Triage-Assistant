# Code Explanations Notes

This file exists because some file formats in the project do not support comments safely.

## Why not comment every file directly?

- `JSON` files do not support comments.
- `package.json` cannot contain normal code comments.
- Some generated config files are better left unchanged until we actually need to edit them.

## Files that currently have in-file teaching comments

- `backend/app/main.py`
- `backend/app/api/routes/health.py`
- `backend/app/core/config.py`
- `backend/app/models/domain.py`
- `backend/app/models/schemas.py`
- `backend/app/services/repository.py`
- `backend/scripts/generate_synthetic_incidents.py`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`

## Learning rule for this repo

For new code we add from now on:

1. Write the code.
2. Add beginner-friendly comments directly in the file.
3. Explain the code in chat as well.
4. Remove or reduce teaching comments later once the concepts are learned.
