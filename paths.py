"""Single source of truth for where data lives.

Nothing else in the repo — scrapers, unify, UI — may build a data path of its
own. The default root is <repo>/data, which is gitignored: each repo carries
the dataset it produces, and nothing large is ever committed.

Repos also need sources they do not produce (news-explorer unifies all four),
so `source_dir()` falls back to the sibling repo that owns a source when this
repo has no copy — see SOURCE_REPO below. That makes the common case need no
configuration at all.

To point a checkout at another disk (a scratch dir, a colleague's export, a
mounted share) without editing code, set the root explicitly — this disables
the sibling fallback, so the root must then hold every source you need:

    NEWS_DATA_DIR=/scratch/news-data  python unify/unify.py
    NEWS_DATA_DIR=/scratch/news-data  streamlit run ui/dataset_explorer.py

or per-run with the `--data-dir` flag every script exposes.

Import it from anywhere in the repo with:

    import paths            # after paths.bootstrap() or a sys.path insert
"""
import argparse
import glob
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

#: env var that overrides the data root for a whole process tree
DATA_DIR_ENV = "NEWS_DATA_DIR"

#: the source datasets this repo collects, in the order the UI lists them
SOURCES = ("ground_news", "gdelt", "eventregistry", "allsides")


def bootstrap() -> str:
    """Make `import paths` work from a subdirectory (ui/, unify/, scrapers/*).

    Streamlit and the scrapers run their files as scripts, so the repo root
    isn't on sys.path — this puts it there. Returns the repo root."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    return REPO_ROOT


def data_dir() -> str:
    """Root of all datasets: $NEWS_DATA_DIR, else <repo>/data."""
    return os.path.abspath(os.environ.get(DATA_DIR_ENV) or os.path.join(REPO_ROOT, "data"))


def use_data_dir(path: str | None) -> str:
    """Point this process (and anything it imports later) at `path`.

    Scripts call this once with their --data-dir value; passing None keeps
    whatever the environment already said."""
    if path:
        os.environ[DATA_DIR_ENV] = os.path.abspath(os.path.expanduser(path))
    return data_dir()


def add_data_dir_arg(parser: argparse.ArgumentParser) -> None:
    """Give a script the standard --data-dir flag."""
    parser.add_argument("--data-dir", default=None,
                        help=f"data root (default: ${DATA_DIR_ENV} or <repo>/data)")


#: which repo owns each source's raw data, now that every repo carries its own
#: data/ directory. The explorer has to read all of them to unify, so it needs
#: to find data it does not own.
SOURCE_REPO = {
    "gdelt": "news-gdelt",
    "ground_news": "news-ground-news",
    "discovery": "news-ground-news",
    "eventregistry": "news-eventregistry",
    "unified": "news-explorer",
}


def source_dir(source: str) -> str:
    """Where one source's raw scraper output lives, e.g. <data>/gdelt.

    Each repo holds its own data/ (gitignored), so the local path is used when
    it exists — that is always the right answer for the repo that produces the
    source. When it does not exist we look in the sibling repo that owns the
    source, which is how news-explorer reaches the collectors' output without a
    shared data root. $NEWS_DATA_DIR still overrides everything.

    Falls back to the local path so that *writes* land under this repo rather
    than in a sibling."""
    local = os.path.join(data_dir(), source)
    if os.path.isdir(local) or os.environ.get(DATA_DIR_ENV):
        return local
    owner = SOURCE_REPO.get(source)
    if owner:
        sibling = os.path.join(os.path.dirname(REPO_ROOT), owner, "data", source)
        if os.path.isdir(sibling):
            return sibling
    return local


def unified_dir() -> str:
    """Where unify.py writes the unified-format datasets the UI reads.

    Owned by news-explorer; resolved through source_dir so the other repos can
    read it too."""
    return source_dir("unified")


def unified_path(source: str) -> str:
    """The unified JSONL for one source ("all" for the concatenation)."""
    return os.path.join(unified_dir(), f"unified_{source}.jsonl")


def unified_datasets() -> list[str]:
    """Every unified dataset present on disk, per-source first and the
    combined unified_all.jsonl last (it is the big one — the UI defaults away
    from it deliberately)."""
    found = {os.path.basename(p): p for p in glob.glob(os.path.join(unified_dir(), "unified_*.jsonl"))}
    ordered = [found.pop(f"unified_{s}.jsonl") for s in SOURCES if f"unified_{s}.jsonl" in found]
    combined = found.pop("unified_all.jsonl", None)
    ordered += [found[k] for k in sorted(found)]          # any source added later
    return ordered + ([combined] if combined else [])


# ── External inputs ──────────────────────────────────────────────────────────
# The AllSides crawl is produced by a separate repo (Qbias), so it lives
# outside this data root. Default: a sibling checkout next to this repo.

QBIAS_DIR_ENV = "QBIAS_DIR"


def qbias_dir() -> str:
    """Root of the Qbias checkout (holds the AllSides crawl + article bodies).

    $QBIAS_DIR wins. Otherwise walk up from this repo looking for qbias/Qbias,
    rather than assuming a fixed depth: these repos sit one level deeper than
    they used to (~/news/<repo> rather than ~/<repo>), and a hard-coded
    os.path.dirname(REPO_ROOT) silently resolved to the wrong place after the
    move. Falls back to ~/qbias/Qbias so the path is still well-defined when
    nothing is found."""
    env = os.environ.get(QBIAS_DIR_ENV)
    if env:
        return os.path.abspath(env)
    here = REPO_ROOT
    for _ in range(4):
        here = os.path.dirname(here)
        if not here or here == os.sep:
            break
        cand = os.path.join(here, "qbias", "Qbias")
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(os.path.expanduser("~"), "qbias", "Qbias"))


def allsides_crawl() -> str:
    """Newest AllSides crawl JSONL in the Qbias checkout ("" if absent)."""
    hits = sorted(glob.glob(os.path.join(qbias_dir(), "allsides_crawl", "output", "allsides_*.jsonl")))
    return hits[-1] if hits else ""


def allsides_bodies_dir() -> str:
    """Qbias multi_source_scrape per-domain body texts, joined onto AllSides
    articles by URL."""
    return os.path.join(qbias_dir(), "multi_source_scrape", "output", "per_domain")


def archive_dir(source: str) -> str:
    """Per-source archive for superseded files. Data is moved here, never
    deleted — see the scripts that rewrite datasets in place."""
    return os.path.join(source_dir(source), "archive")


def label(path: str) -> str:
    """Short display name for a dataset path, relative to the data root."""
    try:
        return os.path.relpath(path, data_dir())
    except ValueError:                                     # different drive
        return path
