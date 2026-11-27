# Single-file submission

Some publishers and typesetting agencies require one `.tex` file with no `\input` and no custom macros.
Using claimlink in this scenario is still possible, we provide an example latexmk file which creates a "flattened tex file" by replacing the claimlink commands and inputs by their values before building the final pdf from this submittable tex file.

## Setup

1. Copy [`latexmkrc`](latexmkrc) to your project root and adjust `$main`, `$claims`, and `$flat`.
2. Build with `latexmk` or use overleaf save.

The `latexmkrc` rewrites the input file before latexmk processes it, so pdflatex reads the flattened `build/paper.tex` instead of `paper.tex`.

## Limits

`\cltable`, `\clusage`, and `\claimlinkusagefile` are not flattened: they are produced during typesetting by the ClaimLink runtime and `.clmdata`, which the generated file no longer contains. This usually isnt a problem though as these tables belong into supplementary documents which typically get submitted as pdf. If a non-submitted document prints another document's usage table, build that source once for the data.

## Overleaf

The generated copy lives in Overleaf's compile sandbox, not in the project file tree, so it is not downloadable from the editor. The PDF you see is still built from it. Build locally or in CI to get the file for submission.
