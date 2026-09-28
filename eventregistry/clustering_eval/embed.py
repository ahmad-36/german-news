"""Embed the eval set with every model x text condition (env: rag, needs a GPU).

  srun -p p_48G --gres=gpu:1 python clustering_eval/embed.py

Conditions: title, title_lede (title + lede) for all four models; body
(title + full body) for BGE-M3 only. Also records, per model x condition, how
many inputs exceeded the model's max_seq_length and were truncated.

Output: data/clustering_eval/emb/<model>__<cond>.npy (L2-normalised float32),
        data/clustering_eval/truncation.json
"""
import json
import os
import time

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "clustering_eval")

MODELS = {  # short name -> (hf id, input prefix)
    "bge-m3": ("BAAI/bge-m3", ""),
    "me5-large": ("intfloat/multilingual-e5-large", "query: "),  # e5's symmetric-task prefix
    "labse": ("sentence-transformers/LaBSE", ""),
    "gbert-large": ("deutsche-telekom/gbert-large-paraphrase-cosine", ""),
}
CONDS = {
    "title": lambda a: a["title"],
    "title_lede": lambda a: f"{a['title']}\n{a['lede']}",
    "body": lambda a: f"{a['title']}\n{a['body']}",
}
PLAN = [(m, c) for m in MODELS for c in ("title", "title_lede")] + [("bge-m3", "body")]
BATCH = {"title": 256, "title_lede": 64, "body": 4}


def truncation_stats(model, texts):
    tok = model.tokenizer
    lens = np.array([len(ids) for ids in tok(texts, add_special_tokens=True,
                                             truncation=False)["input_ids"]])
    cap = model.max_seq_length
    over = lens > cap
    return {
        "max_seq_length": int(cap),
        "n": int(len(lens)),
        "n_truncated": int(over.sum()),
        "pct_truncated": round(100 * over.mean(), 2),
        "tokens_p50": int(np.median(lens)),
        "tokens_p95": int(np.percentile(lens, 95)),
        "tokens_max": int(lens.max()),
        # share of all input tokens the model never saw
        "pct_tokens_dropped": round(100 * np.clip(lens - cap, 0, None).sum() / lens.sum(), 2),
    }


def main():
    arts = [json.loads(l) for l in open(os.path.join(DATA, "articles.jsonl"))]
    os.makedirs(os.path.join(DATA, "emb"), exist_ok=True)
    trunc_path = os.path.join(DATA, "truncation.json")
    trunc = json.load(open(trunc_path)) if os.path.exists(trunc_path) else {}

    for name in MODELS:
        hf_id, prefix = MODELS[name]
        todo = [c for m, c in PLAN if m == name]
        model = None
        for cond in todo:
            out = os.path.join(DATA, "emb", f"{name}__{cond}.npy")
            if os.path.exists(out) and f"{name}__{cond}" in trunc:
                print(f"skip {name}/{cond} (done)")
                continue
            if model is None:
                model = SentenceTransformer(hf_id, device="cuda")
                model.half()
            texts = [prefix + CONDS[cond](a) for a in arts]
            trunc[f"{name}__{cond}"] = truncation_stats(model, texts)
            t0 = time.time()
            emb = model.encode(texts, batch_size=BATCH[cond], normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=False)
            np.save(out, emb.astype(np.float32))
            print(f"{name}/{cond}: {emb.shape} in {time.time() - t0:.0f}s, "
                  f"truncation {trunc[f'{name}__{cond}']}", flush=True)
            json.dump(trunc, open(trunc_path, "w"), indent=2)
        del model
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
