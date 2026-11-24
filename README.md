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

Every call records the value, optionally unit and description, the caller's source location and a timestamp in `claim-lock.json` in the current directory. Re-running a changed value updates the file and emits a warning.

## Install

TODO

## Export to LaTeX

```bash
claimlink export
claimlink export --input claim-lock.json --output generated/claims.tex
```

`claims.tex` is overwritten on every export and contains one block per claim:

```latex
\providecommand{\ClaimValueNumberOfAnalyzedPapers}{124}
\providecommand{\ClaimUnitNumberOfAnalyzedPapers}{papers}
```

Use it in the paper:

```latex
\input{claims.tex}

The analysis includes \ClaimValueNumberOfAnalyzedPapers{} papers.
```

Commit `claim-lock.json`; treat `claims.tex` as a generated artifact.

## Notebooks with nbconvert

JupyterLab works with no extra setup, a plain `jupyter nbconvert --execute` however does not tell the kernel which notebook or cell it is running.
To get these fields, please use our bundled preprocessor instead of `--execute`:

```bash
pip install "claimlink[nbconvert]"

jupyter nbconvert --to notebook \
  --Exporter.preprocessors=claimlink.nbconvert.ClaimLinkPreprocessor \
  paper.ipynb
```
