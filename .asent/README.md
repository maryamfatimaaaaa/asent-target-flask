# ASENT configuration for asent-target-flask

ASENT reads this folder from the BASE commit of every change it gates, so a change cannot loosen
its own rules: a pull request that edits `.asent/` is never ACCEPTed. Schema and rules:
docs/asent-config.md in the ASENT repository.

## CAVR (dependencies)

- Input: the root `requirements.txt`. Every requirement is pinned with `==`.
- `cavr/policy.json` approves exactly those 23 pins and nothing else, so any new package or version
  change is blocked until this policy is changed on the default branch.
- `verify: "changed"`: only requirements added or changed by the base -> head edit are verified.
  A change that does not touch `requirements.txt` has nothing to verify.
- `dependencies.lock.json` (project root) pins every package of the resolved tree (57 releases) with
  the SHA-256 of the real PyPI wheel. Compiled releases list two wheels: CPython 3.12 (the app's
  Dockerfile and ASENT's CI default) and CPython 3.14 (the local ASENT interpreter), both
  manylinux x86_64. Each digest was checked against the downloaded bytes and the PyPI registry.
- `allowed_scopes` grants what the app really does (outbound APIs, database and S3; instance/ files;
  the python3/node code-runner subprocess; secrets from the environment and .env) and denies the rest.

To change a dependency: edit `requirements.txt`, add the new release (and any new transitive
releases) to `dependencies.lock.json` with their wheel digests, and approve the new pin in
`cavr/policy.json` in the same reviewed change to the default branch.
