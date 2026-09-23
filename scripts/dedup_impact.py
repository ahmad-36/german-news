"""Quantify how much of the random-split TF-IDF score is literal duplicate leakage.

`data/unified_allsides/original.jsonl` holds 11,779 records but only 2,807 distinct
article texts -- AllSides reuses the same article across many story pages via its
"More from the Left/Center/Right" sidebars, and `prepare_unified_allsides.py` keeps
one record per (story, slot) rather than per article. The SHA1 split is computed on
`article_id`, so identical texts scatter across train and test.

This script runs the same TF-IDF + LogReg baseline on the set as-is and on a
text-deduplicated version, for the random and outlet-disjoint splits.
"""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR, ANALYSIS_DIR
from splits import LABELS, OUTLET_FOLDS


def texthash(t):
    return hashlib.sha1(t.encode()).hexdigest()


def load():
    return [json.loads(l) for l in open(DATA_DIR / "unified_allsides" / "original.jsonl")]


def dedup(rows):
    """Keep the first record per distinct body text."""
    seen, out = set(), []
    for r in rows:
        h = texthash(r["text"])
        if h in seen:
            continue
        seen.add(h)
        out.append(r)
    return out


def resplit_random(rows, frac_test=0.35):
    """Deterministic split on the TEXT hash, so duplicates cannot straddle splits."""
    out = []
    for r in rows:
        h = int(texthash(r["text"])[:8], 16) / 0xFFFFFFFF
        out.append("test" if h < frac_test else "train")
    return out


def fit_eval(texts, labels, split):
    tr = [i for i, s in enumerate(split) if s == "train"]
    te = [i for i, s in enumerate(split) if s == "test"]
    if not tr or not te:
        return None
    vec = TfidfVectorizer(max_features=50_000, ngram_range=(1, 2),
                          sublinear_tf=True, min_df=3, strip_accents="unicode")
    Xtr = vec.fit_transform([texts[i] for i in tr])
    Xte = vec.transform([texts[i] for i in te])
    ytr = [labels[i] for i in tr]
    yte = [labels[i] for i in te]
    clf = LogisticRegression(max_iter=2000, n_jobs=-1).fit(Xtr, ytr)
    pred = clf.predict(Xte)
    maj = Counter(ytr).most_common(1)[0][0]
    return {
        "accuracy": float(accuracy_score(yte, pred)),
        "macro_f1": float(f1_score(yte, pred, average="macro", labels=LABELS, zero_division=0)),
        "majority_baseline": float(np.mean(np.array(yte) == maj)),
        "n_train": len(tr), "n_test": len(te),
    }


def outlet_split(rows, fold):
    held = set(OUTLET_FOLDS[fold].values())
    return ["test" if r["domain"] in held else "train" for r in rows]


def main():
    rows = load()
    print(f"loaded {len(rows)} records, {len(set(texthash(r['text']) for r in rows))} distinct texts")

    results = {}

    # --- as-is: original article_id split, duplicates straddling train/test ---
    r = fit_eval([x["text"] for x in rows], [x["ground_truth_3class"] for x in rows],
                 [x["split"] for x in rows])
    results["random_asis_with_duplicates"] = r
    print(f"\n[A] random split, AS-IS (duplicates straddle)      acc={r['accuracy']:.3f} "
          f"macroF1={r['macro_f1']:.3f}  n_test={r['n_test']}")

    # --- deduplicated, split on text hash ---
    dd = dedup(rows)
    sp = resplit_random(dd)
    r = fit_eval([x["text"] for x in dd], [x["ground_truth_3class"] for x in dd], sp)
    results["random_deduplicated"] = r
    print(f"[B] random split, DEDUPLICATED                    acc={r['accuracy']:.3f} "
          f"macroF1={r['macro_f1']:.3f}  n_test={r['n_test']}  (majority {r['majority_baseline']:.3f})")

    # --- outlet-disjoint, as-is vs deduplicated ---
    for tag, data in [("as-is", rows), ("dedup", dd)]:
        accs, f1s = [], []
        for fold in range(len(OUTLET_FOLDS)):
            rr = fit_eval([x["text"] for x in data],
                          [x["ground_truth_3class"] for x in data],
                          outlet_split(data, fold))
            if rr:
                accs.append(rr["accuracy"])
                f1s.append(rr["macro_f1"])
        results[f"outlet_{tag}"] = {"accuracy_mean": float(np.mean(accs)),
                                    "accuracy_std": float(np.std(accs)),
                                    "macro_f1_mean": float(np.mean(f1s)),
                                    "folds": len(accs)}
        print(f"[C] outlet-disjoint, {tag:6s}                      "
              f"acc={np.mean(accs):.3f} +/- {np.std(accs):.3f}  macroF1={np.mean(f1s):.3f}")

    out = ANALYSIS_DIR / "dedup_impact.json"
    json.dump(results, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
