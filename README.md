# ClaimLink

Track scientific claims in Python and use their values in LaTeX without copying numbers by hand.

```python
from claimlink import claim

papers = load_papers()

claim(
    "number of analyzed papers",
    len(papers),
    unit="papers",
    description="Total number of papers included in the analysis.",
)
```

Every call records the value, optionally unit and description, the caller's source location and a timestamp in `claim-lock.json` in the project root (the current directory, or `CLAIMLINK_ROOT` when set). Re-running a changed value updates the file and emits a warning.

## Install

TODO

## Export to LaTeX

```bash
claimlink export
claimlink export --input claim-lock.json --output generated/claims.tex
```

`claims.tex` is overwritten on every export and defines one `\csname` block per claim plus a small runtime:

```latex
% key: number-of-analyzed-papers
\expandafter\def\csname clname@number-of-analyzed-papers\endcsname{number of analyzed papers}
\expandafter\def\csname clv@number-of-analyzed-papers\endcsname{124}
\expandafter\def\csname clunit@number-of-analyzed-papers\endcsname{papers}
\expandafter\def\csname cldesc@number-of-analyzed-papers\endcsname{Total number of papers included in the analysis.}
```

Use it in the paper:

```latex
\input{generated/claims.tex}

The analysis includes \clv{number-of-analyzed-papers} papers.
```

Commit `claim-lock.json`; treat `claims.tex` as a generated artifact.

## Claim keys and commands

Keys get derived from the claim name. Names that map to the same key abort the export.

| Command                                        | Effect                                                                |
| ---------------------------------------------- | --------------------------------------------------------------------- |
| `\clv{key}`, `\clunit{key}`, `\cldesc{key}`    | Print the value, unit, or description and record the use.             |
| `\clv*{key}`, `\clunit*{key}`, `\cldesc*{key}` | Print only: no record, anchor, or usage row. For titles and captions. |
| `\clcite{key}`                                 | Print nothing and record a `cite` use.                                |
| `\clvalue{key}`                                | Expandable integer/plain-decimal accessor that records nothing.       |

`\clvalue` is an expandable accessor for integer and plain-decimal claims. It records no usage, so pair it with `\clcite` when the occurrence should be tracked:

```latex
\clcite{retained-findings}\num{\clvalue{retained-findings}}
```

## Claims table and usage (join) table

```latex
\cltable   % tabular, inside a float
\cltable*  % longtable, spans pages, outside floats
\clusage   % usage table built from the previous pass
\clusage*  % longtable usage table
```

## Join table across documents

Each compile writes `<jobname>.clmdata` in the LaTeX build directory. You can print multiple usage tables from those files with no extra CLI step (e.g. to print usage tables for both the main paper as well as the supplement in the supplement):

```latex
\usepackage{longtable}  % required by both commands

\claimlinkusagefile{main}  % rows written by main.tex
\claimlinkusageself        % rows written by this document
```

## Notebooks with nbconvert

JupyterLab works with no extra setup, a plain `jupyter nbconvert --execute` however does not tell the kernel which notebook or cell it is running.
To get these fields, please use our bundled preprocessor instead of `--execute`:

```bash
pip install "claimlink[nbconvert]"

jupyter nbconvert --to notebook \
  --Exporter.preprocessors=claimlink.nbconvert.ClaimLinkPreprocessor \
  paper.ipynb
```
