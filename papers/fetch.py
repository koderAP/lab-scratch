#!/usr/bin/env python3
"""Download author-posted or openly licensed PDFs listed in papers/README.md."""
from __future__ import annotations

import ssl
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CTX = ssl.create_default_context()
UA = "COL868-course-project research reading list (educational)"

PAPERS = [
    ("01-wu-qpr-sigmod2025.pdf", "https://pages.cs.wisc.edu/~wentaowu/papers/sigmod26-qpr-detection.pdf"),
    ("02-wu-hybrid-cost-tkde2024.pdf", "https://pages.cs.wisc.edu/~wentaowu/papers/tkde24-hybrid-cost-modeling.pdf"),
    ("03-wu-sampling-reopt-sigmod2016.pdf", "https://pages.cs.wisc.edu/~wentaowu/papers/sigmod16-reoptimization.pdf"),
    ("04-wu-time-prediction-icde2013.pdf", "https://pages.cs.wisc.edu/~wentaowu/papers/icde13-prediction.pdf"),
    ("05-sql-trek-pvldb2025.pdf", "https://www.vldb.org/pvldb/vol18/p5210-lightstone.pdf"),
    ("06-llminxadvis-arxiv2503.07884.pdf", "https://arxiv.org/pdf/2503.07884"),
    ("07-maadvisor-arxiv2508.16044.pdf", "https://arxiv.org/pdf/2508.16044"),
    ("08-join-synopses-sigmod1999.pdf", "https://www.cs.emory.edu/~cheung/Courses/584/Syllabus/papers/Frequency-count/join-synopses-SIGMOD.pdf"),
    ("09-strat-tods2007.pdf", "https://ranger.uta.edu/~gdas/websitepages/preprints-papers/a9-chaudhuri.pdf"),
    ("10-chaudhuri-aqp-sigmod2001.pdf", "https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/SIG01-AQP.pdf"),
    ("11-autoadmin-index-vldb1997.pdf", "https://www.vldb.org/conf/1997/P146.PDF"),
    ("12-autoadmin-whatif-sigmod1998.pdf", "https://www.csd.uoc.gr/~hy460/pdf/autoadmin_conf_version.pdf"),
    ("13-leis-optimizers-pvldb2015.pdf", "https://www.vldb.org/pvldb/vol9/p204-leis.pdf"),
    ("14-dsb-pvldb2021.pdf", "https://www.vldb.org/pvldb/vol14/p3376-ding.pdf"),
    ("15-joins-on-samples-pvldb2020.pdf", "https://www.vldb.org/pvldb/vol13/p547-huang.pdf"),
    ("16-quickr-sigmod2016.pdf", "https://anilshanbhag.com/static/papers/quickr_sigmod16.pdf"),
    ("17-extend-icde2019.pdf", "https://www.vldb.org/pvldb/vol12/p816-kossmann.pdf"),
    ("18-asqp-rl-arxiv2401.17059.pdf", "https://arxiv.org/pdf/2401.17059"),
    ("19-babcock-dynamic-sample-sigmod2003.pdf", "https://web.stanford.edu/class/cs345d-01/rl/babcock.pdf"),
    ("20-icde2001-sampling-limitations.pdf", "https://web.stanford.edu/class/cs345d-01/rl/chaudhuri2.pdf"),
    ("21-histograms-sigmod1998.pdf", "https://web.stanford.edu/class/cs345d-01/rl/chaudhuri3.pdf"),
    ("22-azure-autoindex-sigmod2019.pdf", "https://www.microsoft.com/en-us/research/wp-content/uploads/2019/02/autoindexing_azuredb.pdf"),
    ("23-dscaler-pvldb2016.pdf", "https://ink.library.smu.edu.sg/cgi/viewcontent.cgi?article=4793&context=sis_research"),
    ("24-touchstone-atc2018.pdf", "https://www.usenix.org/system/files/conference/atc18/atc18-li-yuming.pdf"),
    ("25-blinkdb-eurosys2013.pdf", "https://sameeragarwal.github.io/blinkdb_eurosys13.pdf"),
    ("26-two-level-sampling-sigmod2017.pdf", "https://www.cse.ust.hk/~yike/sigmod17.pdf"),
    ("27-poess-tpcds-vldb2002.pdf", "https://www.vldb.org/conf/2002/S17P03.pdf"),
    ("28-hyperband-jmlr2018.pdf", "https://jmlr.org/papers/volume18/16-558/16-558.pdf"),
    ("29-ai-meets-ai-sigmod2019.pdf", "https://15799.courses.cs.cmu.edu/spring2022/papers/22-learned4/ding-sigmod2019.pdf"),
    ("30-mftune-arxiv2603.16450.pdf", "https://arxiv.org/pdf/2603.16450"),
]


def fetch_one(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=CTX, timeout=45) as r:
        data = r.read()
        ctype = (r.headers.get("Content-Type") or "").lower()
    return data, ctype


def fetch(name: str, url: str) -> str:
    dest = HERE / name
    if dest.exists() and dest.read_bytes()[:4] == b"%PDF":
        return f"SKIP  {name}"
    try:
        data, ctype = fetch_one(url)
    except Exception as e:
        return f"FAIL  {name}  {e}"
    if not data.startswith(b"%PDF") and "pdf" not in ctype:
        return f"FAIL  {name}  not a PDF ({ctype[:40]!r}, {len(data)} bytes)"
    dest.write_bytes(data)
    return f"OK    {name}  {len(data) // 1024} KB"


def main() -> int:
    print("writing into", HERE)
    for name, url in PAPERS:
        print(fetch(name, url), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
