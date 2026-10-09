# ADR 0002: MIT license and license propagation

## Context

The repository was published without a `LICENSE` file, and `README.md` and `CONTRIBUTING.md` stated that no license had been selected. Absence of a license is not neutral: the default is exclusive copyright, so the published source could not lawfully be reused, forked or embedded, which contradicts the reason the project is public. Review comments received before this decision recommended different licenses (MIT in one, Apache-2.0 in another), and the closest comparable project, `Imbad0202/academic-research-skills`, publishes under CC-BY-NC 4.0.

The choice also constrains implementation: a permissive license is incompatible with copyleft dependencies, and an AGPL dependency would make the combined distribution non-compliant. This is already recorded as a constraint on the deferred PDF-extraction work.

## Decision

License the repository under the MIT License, with the copyright notice `Copyright (c) 2026 H66e`. MIT requires the notice to accompany copies of the software, so the license is propagated rather than merely declared:

- `README.md` and `CONTRIBUTING.md` state the license instead of stating that none is chosen.
- `pyproject.toml` declares the SPDX identifier `MIT` and `license-files`, so the built distribution carries the notice.
- `evaluation/package-skill.mjs` adds the repository `LICENSE` to the release archive as `ai-research-mentor/LICENSE`, and `evaluation/check-package.mjs` verifies it, so the downloadable artifact carries the notice too.

## Alternatives

- Apache-2.0: rejected by the owner after the one substantive difference was stated. Apache-2.0 grants patent rights explicitly where MIT is silent, and adds `NOTICE` handling; the owner preferred the shorter, more widely understood license.
- CC-BY-NC 4.0: rejected because it is not a software license, and because its non-commercial restriction would prevent the skill from being embedded in commercial tooling, which is the reuse the project wants to permit.
- No license: rejected as the worst option. It reads as "unlicensed" to potential users while legally reserving all rights, producing the opposite of the intended effect.
- Copyleft (GPL/AGPL): rejected because it would discard the permissive-embedding property and conflict with the independently justified ban on AGPL dependencies.

## Rationale

MIT is the shortest permissive license that is compatible with a dependency-free standard-library runtime, permits commercial embedding, and imposes no notice burden beyond keeping the copyright line. Permissive licensing is also the one competitive property in this category that cannot be matched by adding features: the comparable project's CC-BY-NC 4.0 forbids commercial use, and no amount of engineering changes that.

## Consequences

The copyright holder is recorded as the GitHub account name `H66e`, which points to a reachable owner without publishing a personal name. Changing the holder or the license is a copyright-holder decision and must be applied everywhere the notice is propagated, not only in the root `LICENSE`.

`pyproject.toml` uses the PEP 639 SPDX form, which raises the declared `setuptools` floor to 77. The Python package is an optional development install and is not built by CI, so this floor has no effect on the tested paths; it only affects contributors who build a distribution.

The release archive now contains one more entry than before, and its bytes change. Any consumer that pinned the previous archive hash must re-pin.

Permissive licensing is irreversible for published versions: versions already distributed under MIT may be reused and redistributed under other terms provided the notice is retained, even if the project later relicenses. Adding a dependency with a copyleft or non-commercial license would make the combined distribution non-compliant, so dependency review must check the license before adoption.
