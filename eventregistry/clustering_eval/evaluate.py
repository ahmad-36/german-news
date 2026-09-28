"""Cluster the eval set with every representation x method, score against ER eventUri.

  srun -p p_48G --cpus-per-task=32 --mem=128G python clustering_eval/evaluate.py

Representations: the embeddings from embed.py, TF-IDF (word and char n-gram)
cosine, and the production greedy SequenceMatcher clusterer from
gdelt/gdelt_cluster_bulk.py (title only, as in production).
Methods: agglomerative (cosine distance, average/complete/single linkage,
distance_threshold swept) and HDBSCAN (precomputed cosine distance; noise ->
singletons). Every method clusters each time window independently, as the
GDELT pipeline does. Hyperparameters are chosen by BCubed F1 on dev events and
reported on test events. Metrics: BCubed P/R/F1 and ARI, with the gold label
= eventUri across the whole split (so a window boundary cutting an event
costs recall; the window-oracle row shows that ceiling).

Output: data/clustering_eval/results.json, results.md
"""
import json
import os
import sys
import time
import warnings
from collections import Counter
from itertools import product

import numpy as np
from joblib import Parallel, delayed
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.cluster import HDBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "clustering_eval")
sys.path.insert(0, os.path.join(HERE, "..", "..", "gdelt"))
from gdelt_cluster_bulk import cluster_bucket  # noqa: E402  the production clusterer

# ARI's type_of_target check fires whenever most predicted clusters are small
warnings.filterwarnings("ignore", message="The number of unique classes")

AGG_LINKAGES =("average", "complete", "single")
AGG_THRESH = np.round(np.arange(0.01, 1.001, 0.01), 3)
HDB_GRID = list(product((1, 2, 3), (0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8),
                        ("eom", "leaf")))
SEQ_THRESH = np.round(np.arange(0.30, 0.951, 0.05), 3)
N_BOOT = 2000


# ── metrics ──────────────────────────────────────────────────────────────────

def bcubed_items(gold, pred):
    """Per-item BCubed precision and recall."""
    pair = Counter(zip(gold, pred))
    ng, npred = Counter(gold), Counter(pred)
    p = np.array([pair[(g, q)] / npred[q] for g, q in zip(gold, pred)])
    r = np.array([pair[(g, q)] / ng[g] for g, q in zip(gold, pred)])
    return p, r


def f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def score(gold, pred):
    p, r = bcubed_items(gold, pred)
    P, R = p.mean(), r.mean()
    return {"P": round(P, 4), "R": round(R, 4), "F1": round(f1(P, R), 4),
            "ARI": round(adjusted_rand_score(gold, pred), 4),
            "n_clusters": len(set(pred))}


# ── clustering (per window, labels made global by window prefix) ─────────────

def cos_dist(X):
    if hasattr(X, "toarray"):
        X = X.toarray()
    D = 1.0 - X @ X.T
    np.clip(D, 0.0, 2.0, out=D)
    np.fill_diagonal(D, 0.0)
    return D.astype(np.float64)


def agg_labels(D, method):
    """All thresholds at once: one linkage, many cuts (== sklearn Agglomerative
    with metric='precomputed' cosine and distance_threshold=t)."""
    if len(D) == 1:
        return {t: np.zeros(1, int) for t in AGG_THRESH}
    Z = linkage(squareform(D, checks=False), method=method)
    return {t: fcluster(Z, t=t, criterion="distance") for t in AGG_THRESH}


def hdb_labels(D, ms, eps, sel):
    if len(D) < 3:
        return np.arange(len(D))
    lab = HDBSCAN(metric="precomputed", min_cluster_size=2, min_samples=ms,
                  cluster_selection_epsilon=eps, cluster_selection_method=sel,
                  copy=True).fit_predict(D)
    noise = lab < 0
    lab[noise] = lab.max() + 1 + np.arange(noise.sum())
    return lab


def seq_labels(arts, thresh):
    items = [{"title": a["title"], "_i": i} for i, a in enumerate(arts)]
    lab = np.full(len(arts), -1)
    k = 0
    for c in cluster_bucket(items, thresh, index_top=6):
        for it in c["articles"]:
            lab[it["_i"]] = k
        k += 1
    for i in np.where(lab < 0)[0]:  # titles cluster_bucket skips (no usable tokens)
        lab[i] = k
        k += 1
    return lab


def seq_run(window_arts, thresh):
    """Greedy SequenceMatcher over every window of one split -> global labels."""
    parts, k = [], 0
    for w, arts in enumerate(window_arts):
        parts.append((w, np.arange(k, k + len(arts)), seq_labels(arts, thresh)))
        k += len(arts)
    return globalise(parts)


def globalise(parts):
    """parts: list of (window, idx array, labels) -> one label per item."""
    n = sum(len(ix) for _, ix, _ in parts)
    out = np.empty(n, dtype=object)
    for w, ix, lab in parts:
        for i, l in zip(ix, lab):
            out[i] = f"{w}:{l}"
    return list(out)


# ── representations ──────────────────────────────────────────────────────────

def representations(arts):
    reps = {}
    for f in sorted(os.listdir(os.path.join(DATA, "emb"))):
        if f.endswith(".npy"):
            reps[f[:-4]] = np.load(os.path.join(DATA, "emb", f))
    texts = {"title": [a["title"] for a in arts],
             "title_lede": [f"{a['title']}\n{a['lede']}" for a in arts]}
    for cond, tx in texts.items():
        reps[f"tfidf-word__{cond}"] = TfidfVectorizer(
            lowercase=True, sublinear_tf=True, token_pattern=r"(?u)\b\w\w+\b").fit_transform(tx)
        reps[f"tfidf-char__{cond}"] = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), lowercase=True,
            sublinear_tf=True, min_df=2).fit_transform(tx)
    return reps


def run_rep(name, X, arts, splits):
    """Sweep every (method, params) on dev; score the dev-best on test. Test is
    also swept, only to report how much dev-tuning costs (test_oracle_F1)."""
    scores, preds, keep = {}, {}, {}
    for split, windows in splits.items():
        gold = [arts[i]["event"] for w in windows for i in windows[w]]
        order = np.concatenate([windows[w] for w in windows])
        pos = {int(i): k for k, i in enumerate(order)}
        Ds = {w: cos_dist(X[ix]) for w, ix in windows.items()}
        loc = {w: np.array([pos[int(i)] for i in ix]) for w, ix in windows.items()}

        def record(m, p, pred):
            scores[(m, p, split)] = score(gold, pred)
            if split == "test" and keep.get(m) == p:  # dev runs first
                preds[(m, p)] = pred

        for m in AGG_LINKAGES:
            cuts = {w: agg_labels(Ds[w], m) for w in windows}
            for t in AGG_THRESH:
                record(f"agglo-{m}", f"t={t}",
                       globalise([(w, loc[w], cuts[w][t]) for w in windows]))
        for ms, eps, sel in HDB_GRID:
            record("hdbscan", f"ms={ms},eps={eps},{sel}",
                   globalise([(w, loc[w], hdb_labels(Ds[w], ms, eps, sel)) for w in windows]))
        if split == "dev":
            for m in {m for m, _, _ in scores}:
                params = [p for mm, p, s in scores if mm == m and s == "dev"]
                keep[m] = max(params, key=lambda p: scores[(m, p, "dev")]["F1"])
    out = {}
    for m, bp in keep.items():
        params = [p for mm, p, s in scores if mm == m and s == "test"]
        tb = max(params, key=lambda p: scores[(m, p, "test")]["F1"])
        out[m] = {"params": bp, "dev": scores[(m, bp, "dev")], "test": scores[(m, bp, "test")],
                  "pred_test": preds[(m, bp)], "test_oracle_params": tb,
                  "test_oracle_F1": scores[(m, tb, "test")]["F1"]}
    return name, out


def main():
    t0 = time.time()
    arts = [json.loads(l) for l in open(os.path.join(DATA, "articles.jsonl"))]
    splits = {s: {} for s in ("dev", "test")}
    for i, a in enumerate(arts):
        splits[a["split"]].setdefault(a["window"], []).append(i)
    splits = {s: {w: np.array(ix) for w, ix in sorted(ws.items())} for s, ws in splits.items()}
    golds = {s: [arts[i]["event"] for w in ws for i in ws[w]] for s, ws in splits.items()}

    results = {}  # rep -> method -> {"params", "dev", "test", "pred_test"}
    # window oracle: perfect clustering inside each window
    for s in splits:
        pred = [f"{arts[i]['window']}:{arts[i]['event']}" for w in splits[s] for i in splits[s][w]]
        results.setdefault("oracle", {}).setdefault("window-oracle", {})[s] = score(golds[s], pred)

    # production baseline: greedy SequenceMatcher on titles
    n_jobs = int(os.environ.get("SLURM_CPUS_PER_TASK", 16))
    seq_jobs = [(t, s) for s in splits for t in SEQ_THRESH]
    seq_out = Parallel(n_jobs=n_jobs)(
        delayed(seq_run)([[arts[i] for i in ix] for ix in splits[s].values()], t)
        for t, s in seq_jobs)
    seq = {(t, s): (score(golds[s], pred), pred) for (t, s), pred in zip(seq_jobs, seq_out)}
    best_t = max(SEQ_THRESH, key=lambda t: seq[(t, "dev")][0]["F1"])
    results["seqmatch__title"] = {"greedy-seqmatch": {
        "params": f"t={best_t}", "dev": seq[(best_t, "dev")][0],
        "test": seq[(best_t, "test")][0], "pred_test": seq[(best_t, "test")][1]},
        "greedy-seqmatch@0.65": {
        "params": "t=0.65 (production)", "dev": seq[(0.65, "dev")][0],
        "test": seq[(0.65, "test")][0], "pred_test": seq[(0.65, "test")][1]}}
    print(f"seqmatch done ({time.time() - t0:.0f}s): best t={best_t}", flush=True)

    reps = representations(arts)
    print("representations:", list(reps), flush=True)
    outs = Parallel(n_jobs=min(len(reps), int(os.environ.get("SLURM_CPUS_PER_TASK", 16))),
                    verbose=5)(delayed(run_rep)(n, X, arts, splits) for n, X in reps.items())

    for name, res in outs:
        results[name] = res

    # paired event-level bootstrap on test BCubed F1 for the text-length questions
    test_gold = golds["test"]
    ev = np.array(test_gold)
    uniq = np.unique(ev)
    ev_idx = {e: np.where(ev == e)[0] for e in uniq}
    rng = np.random.default_rng(0)
    boots = [np.concatenate([ev_idx[e] for e in rng.choice(uniq, len(uniq))]) for _ in range(N_BOOT)]

    def best_method(rep):
        return max((m for m in results[rep] if m != "greedy-seqmatch@0.65"),
                   key=lambda m: results[rep][m]["dev"]["F1"])

    def item_pr(rep):
        return bcubed_items(test_gold, results[rep][best_method(rep)]["pred_test"])

    def boot_diff(a, b):
        (pa, ra), (pb, rb) = item_pr(a), item_pr(b)
        d = np.array([f1(pa[ix].mean(), ra[ix].mean()) - f1(pb[ix].mean(), rb[ix].mean())
                      for ix in boots])
        return {"a": a, "b": b, "diff_F1": round(f1(pa.mean(), ra.mean()) - f1(pb.mean(), rb.mean()), 4),
                "ci95": [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)]}

    comps = [("bge-m3__title_lede", "bge-m3__title"), ("bge-m3__body", "bge-m3__title_lede"),
             ("bge-m3__body", "bge-m3__title")]
    for m in ("me5-large", "labse", "gbert-large"):
        comps.append((f"{m}__title_lede", f"{m}__title"))
    for cond in ("title", "title_lede"):
        for m in ("bge-m3", "me5-large", "labse"):
            comps.append((f"gbert-large__{cond}", f"{m}__{cond}"))
    comps += [("bge-m3__body", "tfidf-word__title_lede"),
              ("bge-m3__title_lede", "tfidf-word__title_lede"),
              ("tfidf-word__title_lede", "tfidf-word__title")]
    comps.append(("bge-m3__title", "seqmatch__title"))
    comps.append(("bge-m3__title", "tfidf-char__title"))
    boot = [boot_diff(a, b) for a, b in comps if a in results and b in results]

    trunc = json.load(open(os.path.join(DATA, "truncation.json")))
    for rep in results.values():
        for m in rep.values():
            m.pop("pred_test", None)
    json.dump({"results": results, "bootstrap": boot, "truncation": trunc,
               "n": {s: len(golds[s]) for s in golds},
               "events": {s: len(set(golds[s])) for s in golds}},
              open(os.path.join(DATA, "results.json"), "w"), indent=1)
    write_md(results, boot, trunc, golds)
    print(f"done in {time.time() - t0:.0f}s", flush=True)


def write_md(results, boot, trunc, golds):
    L = [f"# ER eventUri clustering eval\n",
         f"test: {len(golds['test'])} articles / {len(set(golds['test']))} events; "
         f"dev: {len(golds['dev'])} / {len(set(golds['dev']))}\n",
         "| representation | method | params (dev-tuned) | P | R | F1 | ARI | #clusters | F1 if tuned on test |",
         "|---|---|---|---|---|---|---|---|---|"]
    rows = []
    for rep, ms in results.items():
        for m, r in ms.items():
            t = r["test"]
            rows.append((t["F1"], f"| {rep} | {m} | {r.get('params', '')} | {t['P']} | {t['R']} | "
                                  f"{t['F1']} | {t['ARI']} | {t['n_clusters']} | {r.get('test_oracle_F1', '')} |"))
    L += [r for _, r in sorted(rows, key=lambda x: -x[0])]
    L += ["\n## Paired bootstrap (test BCubed F1, a − b, best dev method per rep)\n",
          "| a | b | ΔF1 | 95% CI |", "|---|---|---|---|"]
    L += [f"| {b['a']} | {b['b']} | {b['diff_F1']} | {b['ci95']} |" for b in boot]
    L += ["\n## Truncation\n", "| model/cond | max_seq_len | truncated | % | tokens p50/p95/max | % tokens dropped |",
          "|---|---|---|---|---|---|"]
    L += [f"| {k} | {v['max_seq_length']} | {v['n_truncated']} | {v['pct_truncated']} | "
          f"{v['tokens_p50']}/{v['tokens_p95']}/{v['tokens_max']} | {v['pct_tokens_dropped']} |"
          for k, v in trunc.items()]
    open(os.path.join(DATA, "results.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
