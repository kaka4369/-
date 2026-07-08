# Clean-room notice

This commercial V1 is a new implementation created in `Canvas-SaaS-Commercial`.

- Do not copy source code, styles, prompts, assets, or documentation from the previous non-commercial canvas project into this folder.
- API keys must be provided through environment variables or deployment secrets, not committed files.
- User files are stored under `storage/users/<user_id>/`.
- SQLite is used for V1 bootstrapping. Move to PostgreSQL before high-concurrency public launch.

Third-party runtime dependencies are listed in `requirements.txt`.
