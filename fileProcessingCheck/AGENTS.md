# The Project Management MVP web app

## Business Requirements

This project is to build application which will do sanity check for File processing. 
Key features:
- Frontend is required which will accept Filename, file direction (TI, TO), client operator  as text.
    for example CDTURISGBROR18672 is the filename here file direction is TI hence client operator is GBROR.
    this is telecom domain terminology.
- Connect to dev application (10.0.39.201) and verify steps which are mentioned in docs/PLAN.md
- Database configuration get synced from Test database connection

## Limitations

For the MVP, this will list down missing configurations

For the MVP, it will asked to take actions using button

For the MVP, it will sync from test or other reference as per docs/PLAN.md solutions

## Technical Decisions

- NextJS frontend
- Python FastAPI backend, including serving the static NextJS site at /
- Everything packaged into a Docker container
- Use "uv" as the package manager for python in the Docker container
- Start and Stop server scripts for Mac, PC, Linux in scripts/



## Color Scheme

- Accent Yellow: `#ecad0a` - accent lines, highlights
- Blue Primary: `#209dd7` - links, key sections
- Purple Secondary: `#753991` - submit buttons, important actions
- Dark Navy: `#032147` - main headings
- Gray Text: `#888888` - supporting text, labels

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.

## Working documentation

All documents for planning and executing this project will be in the docs/ directory.
Please review the docs/PLAN.md document before proceeding.