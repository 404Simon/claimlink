"""End-to-end tests: generated claims.tex is compiled with pdflatex."""

import math
import re
import shutil
import subprocess
import zlib

import pytest

from claimlink.latex import claim_key, generate

PDFLATEX = shutil.which("pdflatex")
PDFTOTEXT = shutil.which("pdftotext")
PDFINFO = shutil.which("pdfinfo")

pytestmark = pytest.mark.skipif(
    not (PDFLATEX and PDFTOTEXT), reason="pdflatex and pdftotext are required"
)


def claim(name, value, unit=None, description=None, location=None):
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "description": description,
        "location": (
            {"type": "script", "file": "paper/analysis.py", "line": 1}
            if location is None
            else location
        ),
    }


def registry(*claims):
    return {"schema_version": 1, "claims": {c["name"]: c for c in claims}}


MAIN_CLAIMS = registry(
    claim("number of analyzed papers", 124, "papers", "Total papers."),
    claim("model accuracy", 0.917),
    claim("tiny effect", 0.00001),
    claim("silent claim", "HIDDEN"),
    claim("table only claim", "TBLONLY", "widgets", "Table only row."),
)

MAIN_BODY = r"""
BEFORE\clcite{silent-claim}AFTER

\section{Intro}
Value \clv{number-of-analyzed-papers} and unit \clunit{number-of-analyzed-papers}.
Description: \cldesc{number-of-analyzed-papers}. Tiny: \clv{tiny-effect}.
In math: $x = \clv{tiny-effect}$.

\newpage
\section{Results}
Accuracy \clv{model-accuracy}.

\cltable

\clusage
"""

EXPECTED_CLMDATA = [
    "silent-claim,cite,1,0,1",
    "number-of-analyzed-papers,value,2,1,1",
    "number-of-analyzed-papers,unit,3,1,1",
    "number-of-analyzed-papers,description,4,1,1",
    "tiny-effect,value,5,1,1",
    "tiny-effect,value,6,1,1",
    "model-accuracy,value,7,2,2",
]

# The real 46-claim registry from the OpenAuditOwl paper, embedded so the
# layout tests are independent of external files.
REAL_CLAIMS = [
    ("articles excluded for missing code", 9, "articles", None,
     "notebook", "01_metadata_overview.ipynb", "5", 14),
    ("articles in 2022", 43, "articles", "Articles in the audited corpus published in 2022.",
     "notebook", "01_metadata_overview.ipynb", "3", 19),
    ("articles in 2023", 60, "articles", "Articles in the audited corpus published in 2023.",
     "notebook", "01_metadata_overview.ipynb", "3", 19),
    ("articles in 2024", 57, "articles", "Articles in the audited corpus published in 2024.",
     "notebook", "01_metadata_overview.ipynb", "3", 19),
    ("articles in 2025", 64, "articles", "Articles in the audited corpus published in 2025.",
     "notebook", "01_metadata_overview.ipynb", "3", 19),
    ("articles in 2026", 62, "articles", "Articles in the audited corpus published in 2026.",
     "notebook", "01_metadata_overview.ipynb", "3", 19),
    ("articles with ambiguous lead country", 7, "articles", None,
     "notebook", "02_topic_country_normalization.ipynb", "12", 13),
    ("articles with folded lead country", 34, "articles", None,
     "notebook", "02_topic_country_normalization.ipynb", "10", 14),
    ("articles without GitHub metrics", 19, "articles", None,
     "notebook", "01_metadata_overview.ipynb", "3", 23),
    ("articles without high severity finding", 11, "articles", None,
     "notebook", "03_irs_scores.ipynb", "16", 35),
    ("articles without senior author h-index", 5, "articles", None,
     "notebook", "01_metadata_overview.ipynb", "3", 24),
    ("audited articles", 286, "articles", "Articles in the audited corpus after code screening.",
     "notebook", "01_metadata_overview.ipynb", "3", 21),
    ("author and lab variables", 7, "variables", None,
     "notebook", "04_association_tests.ipynb", "5", 41),
    ("author metadata corrections proposed", 2, "corrections", None,
     "notebook", "01_metadata_overview.ipynb", "13", 25),
    ("bug findings", 1308, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 29),
    ("canonical topic areas", 11, "topic areas", None,
     "notebook", "02_topic_country_normalization.ipynb", "4", 47),
    ("country inclusion threshold", 5, "articles", None,
     "notebook", "02_topic_country_normalization.ipynb", "10", 13),
    ("folded lead countries", 19, "countries", None,
     "notebook", "02_topic_country_normalization.ipynb", "7", 15),
    ("github and citation variables", 4, "variables", None,
     "notebook", "04_association_tests.ipynb", "5", 42),
    ("GitHub corrections proposed", 9, "corrections", None,
     "notebook", "01_metadata_overview.ipynb", "13", 27),
    ("high severity findings", 1020, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 32),
    ("lead countries", 30, "countries", None,
     "notebook", "02_topic_country_normalization.ipynb", "7", 13),
    ("lead country corrections", 3, "corrections", None,
     "notebook", "01_metadata_overview.ipynb", "13", 30),
    ("low severity findings", 1416, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 34),
    ("maximum IRS high", 13, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 41),
    ("maximum IRS low", 33, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 39),
    ("maximum IRS medium", 28, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 37),
    ("maximum yearly median IRS medium", 11, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 43),
    ("median IRS high", 3, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 40),
    ("median IRS low", 15, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 38),
    ("median IRS medium", 10, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 36),
    ("medium severity findings", 1986, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 33),
    ("metadata corrections accepted", 15, "corrections", None,
     "notebook", "01_metadata_overview.ipynb", "13", 28),
    ("metadata corrections proposed", 28, "corrections", None,
     "notebook", "01_metadata_overview.ipynb", "13", 24),
    ("metadata corrections rejected", 13, "corrections", None,
     "notebook", "01_metadata_overview.ipynb", "13", 29),
    ("methodology findings", 577, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 31),
    ("minimum yearly median IRS medium", 9.5, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 42),
    ("mismatch findings", 926, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 30),
    ("missing findings", 1611, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 28),
    ("named lead countries", 11, "countries", None,
     "notebook", "02_topic_country_normalization.ipynb", "7", 14),
    ("OpenAlex corrections proposed", 17, "corrections", None,
     "notebook", "01_metadata_overview.ipynb", "13", 26),
    ("permutations", 9999, "permutations", None,
     "notebook", "04_association_tests.ipynb", "5", 40),
    ("research articles before code screening", 295, "articles", None,
     "notebook", "01_metadata_overview.ipynb", "5", 13),
    ("retained findings", 4422, "findings", None,
     "notebook", "03_irs_scores.ipynb", "16", 27),
    ("share of articles with folded country", 11.9, "%", None,
     "notebook", "02_topic_country_normalization.ipynb", "10", 15),
    ("statistical test families", 14, "tests",
     "Number of (families of) P-values, one per tested variable.",
     "notebook", "04_association_tests.ipynb", "5", 38),
]


def real_registry():
    return registry(*[
        claim(
            name,
            value,
            unit,
            description,
            location={"type": kind, "file": file, "cell_id": cell, "line": line},
        )
        for name, value, unit, description, kind, file, cell, line in REAL_CLAIMS
    ])


def squash(text):
    return re.sub(r"\s+", " ", text)


def pdf_text(pdf_path):
    result = subprocess.run(
        [PDFTOTEXT, "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def pdf_pages(pdf_path):
    if not PDFINFO:
        pytest.skip("pdfinfo is required for the page-count check")
    result = subprocess.run(
        [PDFINFO, str(pdf_path)], capture_output=True, text=True, check=True
    )
    return int(re.search(r"^Pages:\s+(\d+)", result.stdout, re.M).group(1))


def pdf_page_lines(pdf_path, page):
    result = subprocess.run(
        [PDFTOTEXT, "-layout", "-f", str(page), "-l", str(page), str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def pdf_links(pdf_path):
    """Count /Link annotations, including those inside compressed object streams."""
    data = pdf_path.read_bytes()
    blobs = [data]
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            blobs.append(zlib.decompress(match.group(1)))
        except zlib.error:
            pass
    return b"\n".join(blobs).count(b"/Subtype /Link")


def run_document(
    tmp_path, body, claims=MAIN_CLAIMS, preamble="", options="", passes=2
):
    option_arg = "[" + options + "]" if options else ""
    (tmp_path / "claims.tex").write_text(generate(claims), encoding="utf-8")
    (tmp_path / "main.tex").write_text(
        "\\documentclass" + option_arg + "{article}\n"
        + preamble
        + "\n\\input{claims.tex}\n"
        + "\\begin{document}\n"
        + body
        + "\n\\end{document}\n",
        encoding="utf-8",
    )
    texts = []
    for _ in range(passes):
        result = subprocess.run(
            [PDFLATEX, "-interaction=nonstopmode", "main.tex"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout[-4000:]
        texts.append(pdf_text(tmp_path / "main.pdf"))
    return texts


def compile_once(tmp_path, name):
    result = subprocess.run(
        [PDFLATEX, "-interaction=nonstopmode", f"{name}.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout[-4000:]
    return pdf_text(tmp_path / f"{name}.pdf")


def write_claims(tmp_path, claims):
    (tmp_path / "claims.tex").write_text(generate(claims), encoding="utf-8")


def log_text(tmp_path, name="main"):
    return (tmp_path / f"{name}.log").read_text(encoding="utf-8", errors="replace")


def usage_rows(text):
    """Text after the usage-table header, i.e. only the recorded rows."""
    return squash(text).split("Used as", 1)[1]


def assert_no_overfull(tmp_path):
    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "Overfull \\hbox" not in log, log


def assert_no_overfull_vbox(tmp_path):
    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "Overfull \\vbox" not in log, log


def test_two_pass_usage_table_claims_table_and_invisible_cite(tmp_path):
    # The extra preamble input exercises re-input of claims.tex.
    first, second = run_document(
        tmp_path, MAIN_BODY, preamble="\\input{claims.tex}"
    )
    first_text, second_text = squash(first), squash(second)

    assert "BEFOREAFTER" in second_text
    assert "124" in second_text
    assert "papers" in second_text
    assert "Total papers." in second_text
    assert "1 × 10" in second_text
    # This claim is only in \cltable, so deleting the table makes this fail.
    assert "TBLONLY" in second_text
    assert "Table only row." in second_text

    rows = usage_rows(second)
    assert re.search(r"silent claim cite 0 1\b", rows)
    assert re.search(r"number of analyzed papers value 1 1\b", rows)
    assert re.search(r"number of analyzed papers unit 1 1\b", rows)
    assert re.search(r"number of analyzed papers description 1 1\b", rows)
    assert re.search(r"model accuracy value 2 2\b", rows)

    kinds = re.compile(r"\b(?:value|unit|description|cite)\b")
    first_rows = len(kinds.findall(usage_rows(first)))
    second_rows = len(kinds.findall(rows))
    assert first_rows == 0
    assert second_rows >= 6


SUPPLEMENT_PREAMBLE = (
    "\\usepackage{longtable}\n\\usepackage[hidelinks]{hyperref}\n"
)


def two_document_sources(self_body="\\clv{self-value}"):
    main = r"""
\documentclass{article}
\input{claims.tex}
\begin{document}
\section{Intro}
Value \clv{main-value}. Unit \clunit{main-value}. Cite \clcite{main-cite}.
\newpage
\section{Results}
Description \cldesc{main-desc}.
\end{document}
"""
    supplement = (
        "\\documentclass{article}\n"
        + SUPPLEMENT_PREAMBLE
        + "\\input{claims.tex}\n"
        + "\\begin{document}\n"
        + "\\section{Supplement}\n"
        + "Self " + self_body + ".\n"
        + "\\claimlinkusagefile{main}\n"
        + "\\claimlinkusageself\n"
        + "\\end{document}\n"
    )
    return main, supplement


def two_document_claims():
    return registry(
        claim("main value", 7),
        claim("main cite", 8),
        claim("main desc", 9),
        claim("self value", 10),
    )


def test_cross_document_usage_tables(tmp_path):
    write_claims(tmp_path, two_document_claims())
    main, supplement = two_document_sources()
    (tmp_path / "main.tex").write_text(main, encoding="utf-8")
    (tmp_path / "supplement.tex").write_text(supplement, encoding="utf-8")

    for _ in range(2):
        compile_once(tmp_path, "main")
    assert (tmp_path / "main.clmdata").read_text(encoding="utf-8").splitlines() == [
        "main-value,value,1,1,1",
        "main-value,unit,2,1,1",
        "main-cite,cite,3,1,1",
        "main-desc,description,4,2,2",
    ]

    first = squash(compile_once(tmp_path, "supplement"))
    # First supplement run: no self rows yet, but the main file table is full.
    assert "main value value 1 1" in first
    assert "main desc description 2 2" in first
    assert "self value value" not in first
    assert first.count("Used as") == 2

    second = squash(compile_once(tmp_path, "supplement"))
    assert re.search(r"main value value 1 1\b", second)
    assert re.search(r"main value unit 1 1\b", second)
    assert re.search(r"main cite cite 1 1\b", second)
    assert re.search(r"main desc description 2 2\b", second)
    assert re.search(r"self value value 1 1\b", second)
    assert second.count("Used as") == 2

    # Only the self row links; the main rows have their anchors in another PDF.
    assert pdf_links(tmp_path / "supplement.pdf") == 1
    log = log_text(tmp_path, "supplement")
    assert "referenced but does not exist" not in log
    assert "pdfTeX warning (dest)" not in log
    assert "Overfull \\hbox" not in log
    assert "Overfull \\vbox" not in log
    if PDFINFO:
        dests = subprocess.run(
            [PDFINFO, "-dests", str(tmp_path / "supplement.pdf")],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert '"cl:1"' in dests


def test_self_table_is_plain_without_hyperref(tmp_path):
    write_claims(tmp_path, registry(claim("self value", 10)))
    (tmp_path / "reader.tex").write_text(
        "\\documentclass{article}\n"
        "\\usepackage{longtable}\n"
        "\\input{claims.tex}\n"
        "\\begin{document}\n"
        "Value \\clv{self-value}.\n"
        "\\claimlinkusageself\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    for _ in range(2):
        text = squash(compile_once(tmp_path, "reader"))
    assert re.search(r"self value value 0 1\b", text)
    assert pdf_links(tmp_path / "reader.pdf") == 0
    assert "! LaTeX Error" not in log_text(tmp_path, "reader")


def test_malformed_self_line_warns_and_is_repaired(tmp_path):
    write_claims(tmp_path, registry(claim("known", 1)))
    (tmp_path / "main.clmdata").write_text(
        "broken,line,only,three\n", encoding="utf-8"
    )
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n"
        + SUPPLEMENT_PREAMBLE
        + "\\input{claims.tex}\n"
        + "\\begin{document}\n"
        + "Value \\clv{known}.\n"
        + "\\claimlinkusageself\n"
        + "\\end{document}\n",
        encoding="utf-8",
    )

    first = squash(compile_once(tmp_path, "main"))
    assert "malformed usage line in main.clmdata" in log_text(tmp_path)
    assert "known value" not in first
    assert (tmp_path / "main.clmdata").read_text(encoding="utf-8") == (
        "known,value,1,0,1\n"
    )

    second = squash(compile_once(tmp_path, "main"))
    assert "malformed usage line" not in log_text(tmp_path)
    assert re.search(r"known value 0 1\b", second)


def test_usagefile_skips_malformed_field_count(tmp_path):
    write_claims(
        tmp_path,
        registry(claim("main value", 7), claim("main desc", 8)),
    )
    (tmp_path / "extra.clmdata").write_text(
        "main-value,value,1,,iv\n"
        "too,many,fields,one,two,three\n"
        "main-desc,description,2,3,7\n",
        encoding="utf-8",
    )
    (tmp_path / "reader.tex").write_text(
        "\\documentclass{article}\n"
        + SUPPLEMENT_PREAMBLE
        + "\\input{claims.tex}\n"
        + "\\begin{document}\n"
        + "\\claimlinkusagefile{extra}\n"
        + "\\end{document}\n",
        encoding="utf-8",
    )
    text = squash(compile_once(tmp_path, "reader"))
    assert "main value value iv" in text
    assert "main desc description 3 7" in text
    assert "too many fields" not in text
    assert "malformed usage line in extra.clmdata" in log_text(tmp_path, "reader")
    assert "! LaTeX Error" not in log_text(tmp_path, "reader")


@pytest.mark.parametrize(
    "command",
    [r"\claimlinkusagefile{main}", r"\claimlinkusageself"],
    ids=["file", "self"],
)
def test_usage_tables_need_longtable(tmp_path, command):
    (tmp_path / "claims.tex").write_text(
        generate(registry(claim("known", 1))), encoding="utf-8"
    )
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\input{claims.tex}\n"
        "\\begin{document}\n"
        + command
        + "\n\\end{document}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [PDFLATEX, "-interaction=nonstopmode", "main.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "longtable" in log_text(tmp_path)


def test_arraystretch_is_restored_after_claim_tables(tmp_path):
    body = (
        "\\typeout{ARRAYSTRETCH-A=\\arraystretch}\n"
        "\\cltable\n"
        "\\typeout{ARRAYSTRETCH-B=\\arraystretch}\n"
        "\\cltable*\n"
        "\\typeout{ARRAYSTRETCH-C=\\arraystretch}\n"
    )
    run_document(
        tmp_path,
        body,
        claims=registry(claim("alpha", 1)),
        preamble="\\usepackage{longtable}",
    )
    values = re.findall(r"ARRAYSTRETCH-[ABC]=([0-9.]+)", log_text(tmp_path))
    assert len(values) == 3
    assert len(set(values)) == 1


def test_usagefile_missing_or_empty_warns_and_prints_header(tmp_path):
    write_claims(tmp_path, registry(claim("only claim", 1)))
    source = (
        "\\documentclass{article}\n"
        + SUPPLEMENT_PREAMBLE
        + "\\input{claims.tex}\n"
        + "\\begin{document}\n"
        + "\\claimlinkusagefile{missing}\n"
        + "\\end{document}\n"
    )
    (tmp_path / "reader.tex").write_text(source, encoding="utf-8")
    text = squash(compile_once(tmp_path, "reader"))
    assert "Claim Used as Section Page" in text
    assert "no usage data in missing.clmdata" in log_text(tmp_path, "reader")
    assert "! LaTeX Error" not in log_text(tmp_path, "reader")
    assert "Overfull \\hbox" not in log_text(tmp_path, "reader")

    (tmp_path / "empty.clmdata").write_text("\n\n", encoding="utf-8")
    source = source.replace("\\claimlinkusagefile{missing}", "\\claimlinkusagefile{empty}")
    (tmp_path / "reader.tex").write_text(source, encoding="utf-8")
    text = squash(compile_once(tmp_path, "reader"))
    assert "Claim Used as Section Page" in text
    assert "no usage data in empty.clmdata" in log_text(tmp_path, "reader")


def test_usagefile_skips_blank_lines_and_handles_special_fields(tmp_path):
    write_claims(
        tmp_path,
        registry(
            claim("main value", 7),
            claim("main desc", 8),
            claim("2x faster", 9),
        ),
    )
    (tmp_path / "extra.clmdata").write_text(
        "main-value,value,1,,iv\n"
        "   \n"
        "main-desc,description,2,3,7\n"
        "2x-faster,unit,3,2.1,12\n"
        "unknown-key,unit,4,2,4\n",
        encoding="utf-8",
    )
    (tmp_path / "reader.tex").write_text(
        "\\documentclass{article}\n"
        + SUPPLEMENT_PREAMBLE
        + "\\input{claims.tex}\n"
        + "\\begin{document}\n"
        + "\\claimlinkusagefile{extra}\n"
        + "\\end{document}\n",
        encoding="utf-8",
    )
    text = squash(compile_once(tmp_path, "reader"))
    assert "main value value iv" in text
    assert "main desc description 3 7" in text
    assert "2x faster unit 2.1 12" in text
    assert "unknown-key unit 2 4" in text
    assert text.count("main value") == 1
    assert text.count("main desc") == 1
    assert "! LaTeX Error" not in log_text(tmp_path, "reader")
    assert "Overfull \\hbox" not in log_text(tmp_path, "reader")


def test_usagefile_longtable_repeats_header(tmp_path):
    write_claims(tmp_path, registry(claim("main value", 7)))
    (tmp_path / "long.clmdata").write_text(
        "".join(
            f"main-value,value,{number},1,{number}\n" for number in range(1, 101)
        ),
        encoding="utf-8",
    )
    (tmp_path / "reader.tex").write_text(
        "\\documentclass{article}\n"
        + SUPPLEMENT_PREAMBLE
        + "\\input{claims.tex}\n"
        + "\\begin{document}\n"
        + "\\claimlinkusagefile{long}\n"
        + "\\end{document}\n",
        encoding="utf-8",
    )
    text = squash(compile_once(tmp_path, "reader"))
    assert "main value value 1 1" in text
    assert "main value value 1 100" in text
    assert pdf_pages(tmp_path / "reader.pdf") >= 2
    assert text.count("Claim Used as Section Page") >= 2
    assert "Overfull \\vbox" not in log_text(tmp_path, "reader")
    assert "Overfull \\hbox" not in log_text(tmp_path, "reader")


def test_reinput_claims_does_not_duplicate_self_rows(tmp_path):
    write_claims(tmp_path, registry(claim("self value", 10)))
    (tmp_path / "reader.tex").write_text(
        "\\documentclass{article}\n"
        + SUPPLEMENT_PREAMBLE
        + "\\input{claims.tex}\n"
        + "\\begin{document}\n"
        + "\\input{claims.tex}\n"
        + "Value \\clv{self-value}.\n"
        + "\\claimlinkusageself\n"
        + "\\end{document}\n",
        encoding="utf-8",
    )
    for _ in range(2):
        text = compile_once(tmp_path, "reader")
    assert squash(text).count("self value value 0 1") == 1
    assert (tmp_path / "reader.clmdata").read_text(encoding="utf-8").splitlines() == [
        "self-value,value,1,0,1"
    ]


def test_fenced_group_headers_wrap_without_overfull(tmp_path):
    path = (
        "experiments/very/long/directory/structure/results/tables/"
        "some-directory-xxx/final-report-notebook.ipynb"
    )
    write_claims(
        tmp_path,
        registry(
            claim(
                "path claim",
                1,
                location={"type": "script", "file": path, "line": 5},
            )
        ),
    )
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\usepackage{longtable}\n"
        "\\input{claims.tex}\n\\begin{document}\n\\cltable*\n\\end{document}\n",
        encoding="utf-8",
    )
    source = (tmp_path / "claims.tex").read_text(encoding="utf-8")
    assert source.count("\\rule{\\linewidth}{0.4pt}\\par") == 2
    assert "\\textbf{\\textsf{#1}}" in source
    text = squash(compile_once(tmp_path, "main"))
    assert re.sub(r"\s+", "", path) in re.sub(r"\s+", "", text)
    assert "cmtt/bx" not in log_text(tmp_path)
    assert_no_overfull(tmp_path)
    assert_no_overfull_vbox(tmp_path)


def test_clmdata_is_exact_and_truncated_each_pass(tmp_path):
    run_document(tmp_path, MAIN_BODY)
    data = tmp_path / "main.clmdata"
    assert data.read_text(encoding="utf-8").splitlines() == EXPECTED_CLMDATA

    data.write_text(
        data.read_text(encoding="utf-8") + "stale,sentinel,99,9,9\n",
        encoding="utf-8",
    )
    run_document(tmp_path, MAIN_BODY)
    assert data.read_text(encoding="utf-8").splitlines() == EXPECTED_CLMDATA


def test_discarded_measurement_box_does_not_record_clmdata(tmp_path):
    claims = registry(claim("measure key", 7))
    body = (
        "\\sbox0{\\clv{measure-key}}\n"
        "Real \\clv{measure-key}.\n"
        "\\newpage\n"
        "Last \\clv{measure-key}.\n"
    )
    _, second = run_document(tmp_path, body, claims=claims)
    assert "Real 7." in squash(second)
    assert "Last 7." in squash(second)
    assert (tmp_path / "main.clmdata").read_text(encoding="utf-8").splitlines() == [
        "measure-key,value,2,0,1",
        "measure-key,value,3,0,2",
    ]


def test_plain_clv_in_section_title_records_one_occurrence(tmp_path):
    claims = registry(claim("number of analyzed papers", 124))
    body = "\\section{Results \\clv{number-of-analyzed-papers}}\n\\clusage\n"
    _, second = run_document(tmp_path, body, claims=claims)
    assert "Results 124" in squash(second)
    rows = usage_rows(second)
    assert len(re.findall(r"number of analyzed papers value", rows)) == 1


def test_plain_clv_in_caption_records_one_occurrence(tmp_path):
    claims = registry(claim("number of analyzed papers", 124))
    body = (
        "\\begin{figure}\\caption{Cap \\clv{number-of-analyzed-papers}}"
        "\\end{figure}\n\\clusage\n"
    )
    _, second = run_document(tmp_path, body, claims=claims)
    assert "Cap 124" in squash(second)
    rows = usage_rows(second)
    assert len(re.findall(r"number of analyzed papers value", rows)) == 1


def test_starred_variants_in_moving_arguments_print_but_do_not_record(tmp_path):
    claims = registry(
        claim("number of analyzed papers", 124, "papers", "Total papers."),
        claim("silent claim", "SENTINELCITE"),
    )
    body = (
        "\\section{Results \\clv*{number-of-analyzed-papers} "
        "\\clunit*{number-of-analyzed-papers} \\clcite{silent-claim}}\n"
        "\\begin{figure}\\caption{Cap \\clv*{number-of-analyzed-papers} "
        "\\cldesc*{number-of-analyzed-papers}}\\end{figure}\n"
        "\\clusage\n"
    )
    _, second = run_document(tmp_path, body, claims=claims)
    text = squash(second)
    assert "Results 124 papers" in text
    assert "Cap 124 Total papers." in text

    data = tmp_path / "main.clmdata"
    assert data.read_text(encoding="utf-8").splitlines() == [
        "silent-claim,cite,1,1,1"
    ]
    rows = usage_rows(second)
    assert re.search(r"silent claim cite 1 1\b", rows)
    assert "number of analyzed papers" not in rows


def test_clvalue_is_expandable_for_siunitx_and_records_nothing(tmp_path):
    claims = registry(claim("retained findings", 124, "findings"))
    body = (
        "Text: \\num{\\clvalue{retained-findings}}\n"
        "Math: $\\num{\\clvalue{retained-findings}}$\n"
        "\\clusage\n"
    )
    _, second = run_document(
        tmp_path, body, claims=claims, preamble="\\usepackage{siunitx}"
    )
    text = squash(second)
    assert "Text: 124" in text
    assert "Math: 124" in text
    assert (tmp_path / "main.clmdata").read_text(encoding="utf-8") == ""


def test_toc_plain_form_records_and_star_form_does_not(tmp_path):
    claims = registry(claim("alpha", 124))
    tocs = "\\tableofcontents\n"

    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    _, plain = run_document(
        plain_dir,
        tocs + "\\section{Results \\clv{alpha}}\n\\clusage\n",
        claims=claims,
    )
    assert "Results 124" in squash(plain)
    assert (plain_dir / "main.clmdata").read_text(encoding="utf-8").splitlines() == [
        "alpha,value,1,0,1",
        "alpha,value,2,1,1",
    ]

    star_dir = tmp_path / "star"
    star_dir.mkdir()
    _, star = run_document(
        star_dir,
        tocs + "\\section{Results \\clv*{alpha}}\n\\clusage\n",
        claims=claims,
    )
    assert "Results 124" in squash(star)
    assert "alpha value" not in usage_rows(star)
    assert (star_dir / "main.clmdata").read_text(encoding="utf-8") == ""


def test_output_directory_still_finds_clm(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (tmp_path / "claims.tex").write_text(
        generate(registry(claim("only claim", 7))), encoding="utf-8"
    )
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\input{claims.tex}\n"
        "\\begin{document}\n\\section{Results}\nValue \\clv{only-claim}.\n"
        "\\clusage\n\\end{document}\n",
        encoding="utf-8",
    )
    for _ in range(2):
        result = subprocess.run(
            [
                PDFLATEX,
                "-interaction=nonstopmode",
                "-output-directory=out",
                "main.tex",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout[-4000:]
    assert (out / "main.clm").exists()
    text = squash(pdf_text(out / "main.pdf"))
    assert re.search(r"only claim value 1 1\b", usage_rows(text))


def test_tilde_and_caret_strings_render_in_text_and_math(tmp_path):
    claims = registry(claim("tilde caret", "a~b^c"))
    body = "Text: \\clv{tilde-caret}\nMath: $y=\\clv{tilde-caret}$\n"
    _, second = run_document(tmp_path, body, claims=claims)
    text = squash(second)
    # OT1 maps \textasciitilde/\textasciicircum to the spacing accent glyphs.
    normalized = text.replace("\u02dc", "~").replace("\u02c6", "^")
    assert normalized.count("a~b^c") == 2


def test_hyperref_links_and_usage_table(tmp_path):
    _, second = run_document(
        tmp_path, MAIN_BODY, preamble="\\usepackage{hyperref}"
    )
    assert pdf_links(tmp_path / "main.pdf") > 0
    rows = usage_rows(second)
    assert re.search(r"number of analyzed papers value 1 1\b", rows)
    assert re.search(r"model accuracy value 2 2\b", rows)

    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "referenced but does not exist" not in log
    assert "pdfTeX warning (dest)" not in log

    if not PDFINFO:
        pytest.skip("pdfinfo is required for the destination check")
    dests = subprocess.run(
        [PDFINFO, "-dests", str(tmp_path / "main.pdf")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert '"cl:1"' in dests
    assert '"cl:2"' in dests


def test_cleveref_loaded_after_runtime_does_not_collide(tmp_path):
    claims = registry(
        *[claim(f"claim {i}", i, "units", f"Desc {i}.") for i in range(1, 13)]
    )
    (tmp_path / "claims.tex").write_text(generate(claims), encoding="utf-8")
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\usepackage{longtable}\n"
        "\\usepackage[hidelinks]{hyperref}\n"
        "\\input{claims.tex}\n"
        "\\usepackage{cleveref}\n"
        "\\begin{document}\n"
        "\\section{Results}\\label{sec:one}\n"
        "Value \\clv{claim-1}; cited \\clcite{claim-2}.\n"
        "\\begin{figure}[h]\\caption{A figure.}\\label{fig:one}\\end{figure}\n"
        "See \\cref{sec:one} and \\cref{fig:one}.\n"
        "\\cltable*\n"
        "\\newpage\n"
        "\\clusage*\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    for _ in range(2):
        result = subprocess.run(
            [PDFLATEX, "-interaction=nonstopmode", "main.tex"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout[-4000:]
    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "! LaTeX Error" not in log
    assert "extra }" not in log
    assert "@cref@stack@top" not in log


def test_multipage_use_reports_page_two(tmp_path):
    claims = registry(claim("only claim", 7))
    body = "First page.\n\\newpage\n\\section{Later}\nSee \\clv{only-claim}.\n\\clusage\n"
    _, second = run_document(tmp_path, body, claims=claims)
    assert re.search(r"only claim value 1 2\b", usage_rows(second))


def test_special_characters_and_multiline_description(tmp_path):
    value = '% $ & # _ { } ~ ^ \\ < > | "'
    claims = registry(
        claim("weird value", value, description="line one\nline two"),
        claim("silent claim", "SENTINELCITE"),
    )
    body = (
        "BEFORE\\clcite{silent-claim}AFTER\n"
        "\\clv{weird-value}\n"
        "\\cldesc{weird-value}\n"
    )
    _, second = run_document(tmp_path, body, claims=claims)
    text = squash(second)
    assert "BEFOREAFTER" in text
    assert "% $ & #" in text
    assert "< > |" in text
    assert "line one line two" in text


def test_real_46_claim_table_is_one_page(tmp_path):
    # The real supplement is A4 with 2.5 cm margins; letter paper is too short.
    _, second = run_document(
        tmp_path,
        "\\cltable*\n",
        claims=real_registry(),
        preamble=(
            "\\usepackage{longtable}\n"
            "\\usepackage[a4paper,margin=2.5cm]{geometry}"
        ),
        options="a4paper",
    )
    text = squash(second)
    assert pdf_pages(tmp_path / "main.pdf") == 1
    assert "methodology findings" in text
    assert "9999" in text
    assert "Claim Value Location Description" in text
    assert "Unit" not in text

    # The first data row must share one baseline: a blank claim cell or a
    # value/location line without the claim name means the header shifted it.
    first_row = next(
        line for line in second.splitlines() if "research articles" in line
    )
    assert "295" in first_row
    assert "cell 5, line 13" in first_row
    assert_no_overfull(tmp_path)


@pytest.mark.parametrize("size", [10, 11, 12])
def test_table_width_warning_uses_header_metrics(tmp_path, size):
    options = f"{size}pt"

    narrow = tmp_path / "narrow"
    narrow.mkdir()
    run_document(
        narrow,
        "\\cltable\n",
        claims=registry(claim("alpha", 1, "unit", "Description")),
        preamble="\\usepackage{geometry}\n\\geometry{textwidth=150pt}",
        options=options,
    )
    log = (narrow / "main.log").read_text(encoding="utf-8", errors="replace")
    assert log.count("needs at least") == 1
    match = re.search(r"needs at least ([\d.]+)pt", log)
    assert match, log
    minimum = float(match.group(1))
    # Pins the measurement to \scriptsize: \normalsize would be 302/337pt.
    assert minimum < (240 if size == 10 else 260)

    # One point below the computed metric minimum warns; the ceiling does not.
    for label, width, warns in (
        ("below", math.floor(minimum) - 1, True),
        ("above", math.ceil(minimum), False),
    ):
        directory = tmp_path / label
        directory.mkdir()
        run_document(
            directory,
            "\\cltable*\n",
            claims=real_registry(),
            preamble=(
                "\\usepackage{longtable}\n"
                "\\usepackage{geometry}\n"
                f"\\geometry{{textwidth={width}pt}}"
            ),
            options=options,
        )
        edge_log = (directory / "main.log").read_text(
            encoding="utf-8", errors="replace"
        )
        assert ("needs at least" in edge_log) is warns
        if not warns:
            assert_no_overfull(directory)


def test_12pt_full_width_table_has_no_overfull(tmp_path):
    run_document(
        tmp_path,
        "\\cltable*\n",
        claims=real_registry(),
        preamble="\\usepackage{longtable}",
        options="12pt",
    )
    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "needs at least" not in log
    assert_no_overfull(tmp_path)


@pytest.mark.parametrize(
    "path",
    [
        "experiments/very/long/directory/structure/results/tables/"
        "some-directory-xxx/final-report-notebook.ipynb",
        "experiments/very/long/directory/structure/results/tables/"
        "long-directory-name-for-notes-data/final-report-notebook.ipynb",
        "experiments/very/long/directory/structure/results/tables/"
        "some-directory-xxx/long-directory-name-for-notebook-data/appendice/"
        "supplement/materials/scripts/intermediate/cleane/final-report-notebook.ipynb",
        "/srv/claimlink/project/notebooks/absolute-report.ipynb",
    ],
    ids=["103", "119", "200", "absolute"],
)
def test_long_file_paths_wrap_without_overfull(tmp_path, path):
    claims = registry(
        claim("path claim", 1, location={"type": "script", "file": path, "line": 5})
    )
    _, second = run_document(tmp_path, "\\cltable\n", claims=claims)
    compact = re.sub(r"\s+", "", second)
    assert re.sub(r"\s+", "", path) in compact
    assert_no_overfull(tmp_path)


def test_no_location_group_and_special_file_and_unit(tmp_path):
    claims = registry(
        claim("no location claim", 1, location={}),
        claim(
            "special claim",
            5,
            "50%_done",
            "Special unit.",
            location={
                "type": "script",
                "file": "results_50%/part%20.ipynb",
                "line": 5,
            },
        ),
        claim("uncertain claim", 2, location={"file": "unknown", "line": 3}),
    )
    _, second = run_document(tmp_path, "\\cltable\n", claims=claims)
    text = squash(second)
    assert "(no location)" in text
    assert "unknown" in text
    assert "50%/part" in text
    assert "20.ipynb" in text
    assert re.search(r"5\s+50%", text)
    assert_no_overfull(tmp_path)


def test_group_header_is_never_the_last_line(tmp_path):
    # 65 rows put the second group header exactly at the page boundary; without
    # \\* the header would be stranded at the bottom of the previous page.
    long_group = [
        claim(
            f"long claim {i:02d}",
            i,
            "units",
            location={"type": "script", "file": "paper/long-group.py", "line": i},
        )
        for i in range(1, 66)
    ]
    short_group = [
        claim(
            f"short claim {i}",
            i,
            location={"type": "script", "file": "paper/short-group.py", "line": i},
        )
        for i in range(1, 4)
    ]
    run_document(
        tmp_path,
        "\\cltable*\n",
        claims=registry(*long_group, *short_group),
        preamble="\\usepackage{longtable}",
    )
    headers = {"paper/long-group.py", "paper/short-group.py"}
    pages = pdf_pages(tmp_path / "main.pdf")
    assert pages >= 2
    found_short = False
    for page in range(1, pages + 1):
        lines = pdf_page_lines(tmp_path / "main.pdf", page)
        content = [line for line in lines if not re.fullmatch(r"\d+", line)]
        assert content[-1] not in headers
        text = " ".join(lines)
        if "paper/short-group.py" in text:
            found_short = True
            assert "short claim 1" in text
    assert found_short


def test_claims_table_groups_by_file_and_shows_provenance(tmp_path):
    notebook = {"type": "notebook", "file": "notebooks/result_50%.ipynb"}
    claims = registry(
        claim(
            "number of analyzed papers",
            124,
            "papers",
            "Total papers.",
            location={"type": "script", "file": "paper/analysis.py", "line": 5},
        ),
        claim(
            "notebook claim",
            7,
            "GB",
            "From a cell.",
            location={**notebook, "cell_id": "13", "line": 32},
        ),
        claim(
            "second notebook claim",
            3,
            location={**notebook, "cell_id": "2", "line": 4},
        ),
    )
    _, second = run_document(tmp_path, "\\cltable\n", claims=claims)
    text = squash(second)

    assert "paper/analysis.py" in text
    # pdftotext renders the cmtt underscore as a space; the percent survives.
    assert "50%.ipynb" in text
    assert text.count("paper/analysis.py") == 1
    assert text.count("50%.ipynb") == 1
    assert text.index("50%.ipynb") < text.index("paper/analysis.py")
    assert "cell 13, line 32" in text
    assert "cell 2, line 4" in text
    assert "line 5" in text
    # The value and its unit share one cell; the Unit column is gone.
    assert re.search(r"124\s+papers", text)
    assert re.search(r"7\s+GB", text)
    assert "Total papers." in text
    assert "From a cell." in text
    assert "Location" in text
    assert "Unit" not in text
    assert_no_overfull(tmp_path)


def test_forty_six_claim_longtable_spans_pages_with_repeated_header(tmp_path):
    claims = registry(
        *[
            claim(
                f"claim {i:02d}",
                i,
                "units",
                f"Description {i:02d}.",
                location={
                    "type": "notebook",
                    "file": "paper/results.ipynb",
                    "cell_id": f"cell-{i}",
                    "line": i,
                },
            )
            for i in range(1, 47)
        ]
    )
    # Starting low on the page forces the 46 rows over a page boundary.
    body = "\\vspace*{0.8\\textheight}\n\\cltable*\n"
    _, second = run_document(
        tmp_path, body, claims=claims, preamble="\\usepackage{longtable}"
    )
    text = squash(second)
    assert "claim 01" in text
    assert "claim 46" in text
    assert text.count("Description") >= 3
    assert "Location" in text
    assert text.count("Location") >= 2  # header repeats on the next page
    assert pdf_pages(tmp_path / "main.pdf") >= 2
    assert_no_overfull_vbox(tmp_path)


def test_empty_claims_table_is_header_only(tmp_path):
    _, second = run_document(tmp_path, "\\cltable\n", claims=registry())
    text = squash(second)
    assert "Claim Value Location Description" in text
    assert "unknown" not in text
    assert text.count("Claim") == 1
    assert_no_overfull(tmp_path)


def test_many_claims_table_compiles_and_shows_first_and_last(tmp_path):
    claims = registry(
        *[
            claim(f"claim {i:04d}", i, "units", f"Description {i}.")
            for i in range(1, 1001)
        ]
    )
    # One huge page keeps the unbreakable 1000-row tabular visible to pdftotext.
    preamble = (
        "\\usepackage[paperheight=12000pt,paperwidth=1200pt,margin=10pt]{geometry}"
    )
    _, second = run_document(
        tmp_path, "\\cltable\n", claims=claims, preamble=preamble
    )
    text = squash(second)
    assert "claim 0001" in text
    assert "claim 1000" in text


@pytest.mark.parametrize(
    ("command", "preamble"),
    [
        ("\\cltable\n", "\\usepackage{array}"),
        ("\\cltable*\n", "\\usepackage{array}\n\\usepackage{longtable}"),
    ],
    ids=["tabular", "longtable"],
)
def test_cltable_star_expands_preamble_with_array_loaded(
    tmp_path, command, preamble
):
    _, second = run_document(
        tmp_path,
        command,
        claims=registry(claim("only claim", 4242)),
        preamble=preamble,
    )
    text = squash(second)
    assert "only claim" in text
    assert "4242" in text


def test_cltable_star_breaks_across_pages(tmp_path):
    claims = registry(
        *[
            claim(f"claim {i:04d}", i, "units", f"Description {i}.")
            for i in range(1, 121)
        ]
    )
    body = "\\cltable*\n" + "\\newpage\nFiller page.\n" * 5
    _, second = run_document(
        tmp_path, body, claims=claims, preamble="\\usepackage{longtable}"
    )
    text = squash(second)
    assert "claim 0001" in text
    assert "claim 0120" in text
    assert second.count("Claim") >= 2  # header repeats on later pages
    assert text.count("paper/analysis.py") == 1  # one group header
    assert second.count("\f") >= 6
    assert_no_overfull_vbox(tmp_path)


def test_many_group_headers_across_longtable_pages(tmp_path):
    claims = registry(
        *[
            claim(
                f"claim {group:02d}-{number:02d}",
                number,
                "units",
                f"Description {group:02d}-{number:02d}.",
                location={
                    "type": "script",
                    "file": f"paper/group{group:02d}.py",
                    "line": number,
                },
            )
            for group in range(20)
            for number in range(1, 51)
        ]
    )
    _, second = run_document(
        tmp_path, "\\cltable*\n", claims=claims, preamble="\\usepackage{longtable}"
    )
    text = squash(second)
    assert pdf_pages(tmp_path / "main.pdf") >= 2
    assert "claim 00-01" in text
    assert "claim 19-50" in text
    assert "paper/group00.py" in text
    assert "paper/group19.py" in text
    assert_no_overfull(tmp_path)
    assert_no_overfull_vbox(tmp_path)
    assert "! LaTeX Error" not in log_text(tmp_path)


def test_cltable_unstarred_still_works_in_float(tmp_path):
    claims = registry(claim("alpha", 1, "unit", "description"))
    body = (
        "\\begin{table}[h]\n\\centering\n\\cltable\n"
        "\\caption{A claims table.}\n\\end{table}\n"
    )
    _, second = run_document(tmp_path, body, claims=claims)
    assert "alpha" in squash(second)
    assert "line 1" in squash(second)


@pytest.mark.parametrize(
    "command", [r"\clusage", r"\clusage*"], ids=["short", "long"]
)
def test_usage_tables_fit_long_kind_and_header(tmp_path, command):
    claims = registry(claim("described claim", 1, description="Desc."))
    _, second = run_document(
        tmp_path,
        "\\cldesc{described-claim}\n\n" + command + "\n",
        claims=claims,
        preamble="\\usepackage{longtable}",
    )
    text = squash(second)
    assert "Used as" in text
    assert "described claim description" in text
    assert_no_overfull(tmp_path)


def test_clusage_star_breaks_across_pages(tmp_path):
    claims = registry(
        *[claim(f"claim {i:04d}", i) for i in range(1, 121)]
    )
    uses = "".join(
        f"Value \\clv{{claim-{i:04d}}}.\n" for i in range(1, 121)
    )
    _, second = run_document(
        tmp_path,
        uses + "\\clusage*\n",
        claims=claims,
        preamble="\\usepackage{longtable}\n\\usepackage[hidelinks]{hyperref}",
    )
    text = squash(second)
    assert "claim 0001" in text
    assert "claim 0120" in text
    assert len(re.findall(r"claim \d{4}", second)) == 120
    assert second.count("Claim") >= 2
    assert_no_overfull_vbox(tmp_path)

    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "pdfTeX warning (dest)" not in log
    assert "referenced but does not exist" not in log
    assert pdf_links(tmp_path / "main.pdf") == 120

    if PDFINFO:
        dests = subprocess.run(
            [PDFINFO, "-dests", str(tmp_path / "main.pdf")],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert '"cl:1"' in dests
        assert '"cl:120"' in dests


@pytest.mark.parametrize("command", ["\\cltable*", "\\clusage*"])
def test_star_variants_need_longtable(tmp_path, command):
    (tmp_path / "claims.tex").write_text(
        generate(registry(claim("known", 1))), encoding="utf-8"
    )
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\input{claims.tex}\n"
        "\\begin{document}\n" + command + "\n\\end{document}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [PDFLATEX, "-interaction=nonstopmode", "main.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "longtable" in log


def test_letter_class_records_zero_section(tmp_path):
    claims = registry(claim("letter claim", 7), claim("silent letter", "x"))
    (tmp_path / "claims.tex").write_text(generate(claims), encoding="utf-8")
    (tmp_path / "main.tex").write_text(
        "\\documentclass{letter}\n\\input{claims.tex}\n"
        "\\begin{document}\n\\clv{letter-claim}\n\\clcite{silent-letter}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [PDFLATEX, "-interaction=nonstopmode", "main.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout[-4000:]
    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "Undefined control sequence" not in log
    assert (tmp_path / "main.clmdata").read_text(encoding="utf-8").splitlines() == [
        "letter-claim,value,1,0,1",
        "silent-letter,cite,2,0,1",
    ]


def test_long_usage_name_wraps_without_overfull(tmp_path):
    name = ("long claim name " * 9).strip()
    key = claim_key(name)
    assert len(name) >= 140
    claims = registry(claim(name, 7))

    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    run_document(plain_dir, f"\\clv{{{key}}}\n\\clusage\n", claims=claims)
    assert_no_overfull(plain_dir)

    star_dir = tmp_path / "star"
    star_dir.mkdir()
    run_document(
        star_dir,
        f"\\clv{{{key}}}\n\\clusage*\n",
        claims=claims,
        preamble="\\usepackage{longtable}\n\\usepackage[hidelinks]{hyperref}",
    )
    assert_no_overfull(star_dir)


@pytest.mark.parametrize(
    "command",
    [
        "\\clv{nope}",
        "\\clv*{nope}",
        "\\clunit{nope}",
        "\\clunit*{nope}",
        "\\cldesc{nope}",
        "\\cldesc*{nope}",
        "\\clcite{nope}",
        "\\clvalue{nope}",
    ],
)
def test_unknown_key_is_a_latex_error(tmp_path, command):
    (tmp_path / "claims.tex").write_text(
        generate(registry(claim("known", 1))), encoding="utf-8"
    )
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\input{claims.tex}\n"
        "\\begin{document}\n" + command + "\n\\end{document}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [PDFLATEX, "-interaction=nonstopmode", "main.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    log = (tmp_path / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "unknown claim key" in log
