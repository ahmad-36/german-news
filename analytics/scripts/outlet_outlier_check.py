"""Outlier check: how often does an LLM's per-article stance disagree with the
outlet-level AllSides label?

AllSides rates outlets, not articles (100% label purity across all 15 domains in
`data/unified_allsides/original.jsonl`). So every Fox News article is labelled
`right` whether or not its own content leans right. This script measures the
disagreement rate per outlet: all Fox articles, plus a capped sample of every
other outlet so the Fox number has a baseline to sit against.

Prediction is the argmax over the first generated token restricted to the three
label words, which also yields a calibrated-ish confidence per article for free.
Greedy/deterministic, consistent with the July runs.

Run on SLURM (login node has CUDA_VISIBLE_DEVICES=-1):
    srun --partition=p_80G --gres=gpu:h100:1 python outlet_outlier_check.py
"""

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    MODEL_LLM, DATA_DIR, RESULTS_DIR,
    LLM_SYSTEM_PROMPT, LLM_USER_PROMPT_3CLASS, LABEL_3CLASS,
)

EVAL_FILE = DATA_DIR / "unified_allsides" / "original.jsonl"
OUT_FILE = RESULTS_DIR / "outlet_outlier_3class.jsonl"
FOCUS_DOMAIN = "foxnews.com"


def select_articles(focus, cap, seed=0):
    """All articles from `focus`; up to `cap` per other outlet, deterministic."""
    import hashlib

    by_domain = {}
    with open(EVAL_FILE) as f:
        for line in f:
            r = json.loads(line)
            by_domain.setdefault(r["domain"], []).append(r)

    selected = []
    for domain, arts in sorted(by_domain.items()):
        if domain == focus:
            selected.extend(arts)
            continue
        # deterministic subsample: rank by hash of article_id, take the first `cap`
        arts = sorted(
            arts,
            key=lambda a: hashlib.sha1(f"{seed}:{a['article_id']}".encode()).hexdigest(),
        )
        selected.extend(arts[:cap])
    return selected


def label_token_ids(tokenizer):
    """First-token id for each label word, as it appears after 'Stance:' (leading space)."""
    ids = {}
    for label in LABEL_3CLASS:
        toks = tokenizer.encode(label, add_special_tokens=False)
        toks_sp = tokenizer.encode(" " + label, add_special_tokens=False)
        # the model may emit either the bare or space-prefixed variant; keep both
        ids[label] = sorted({toks[0], toks_sp[0]})
    return ids


def truncate(text, tokenizer, max_len=8000):
    toks = tokenizer(text, add_special_tokens=False)["input_ids"]
    if len(toks) <= max_len:
        return text
    return tokenizer.decode(toks[:max_len], skip_special_tokens=True)


def classify(text, model, tokenizer, device, lab_ids):
    messages = [
        {"role": "system", "content": LLM_SYSTEM_PROMPT},
        {"role": "user", "content": LLM_USER_PROMPT_3CLASS.format(article_text=text)},
    ]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        logits = model(**inputs).logits[0, -1].float()

    # score each label by its best first-token variant, then softmax over the three
    scores = torch.tensor(
        [max(logits[i].item() for i in lab_ids[label]) for label in LABEL_3CLASS]
    )
    probs = torch.softmax(scores, dim=0)
    best = int(torch.argmax(probs))
    return LABEL_3CLASS[best], {l: round(p, 5) for l, p in zip(LABEL_3CLASS, probs.tolist())}


def load_done(path):
    done = set()
    if path.exists():
        with open(path) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["article_id"])
                except json.JSONDecodeError:
                    continue
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=250,
                    help="max articles per non-focus outlet")
    ap.add_argument("--focus", default=FOCUS_DOMAIN)
    ap.add_argument("--limit", type=int, default=0, help="debug: stop after N")
    ap.add_argument("--out", default=str(OUT_FILE))
    args = ap.parse_args()

    out_path = Path(args.out)
    articles = select_articles(args.focus, args.cap)
    done = load_done(out_path)
    pending = [a for a in articles if a["article_id"] not in done]
    if args.limit:
        pending = pending[: args.limit]

    print(f"Selected {len(articles)} articles ({len(done)} already done, "
          f"{len(pending)} pending)")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device} | loading {MODEL_LLM} in BF16...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_LLM)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_LLM, torch_dtype=torch.bfloat16, device_map="auto"
    )
    model.eval()
    lab_ids = label_token_ids(tokenizer)
    print(f"  label first-token ids: {lab_ids}")

    start = time.time()
    with open(out_path, "a") as out_f:
        for art in tqdm(pending, desc="outlier-check"):
            text = truncate(art["text"], tokenizer)
            pred, probs = classify(text, model, tokenizer, device, lab_ids)
            gold = art["ground_truth_3class"]
            out_f.write(json.dumps({
                "article_id": art["article_id"],
                "domain": art["domain"],
                "story_id": art["story_id"],
                "date": art["date"],
                "char_len": art["char_len"],
                "gold_3class": gold,
                "gold_5class": art["ground_truth_5class"],
                "pred_3class": pred,
                "probs": probs,
                "agree": pred == gold,
            }, ensure_ascii=False) + "\n")
            out_f.flush()

    print(f"Done: {len(pending)} predictions in {time.time() - start:.0f}s -> {out_path}")


if __name__ == "__main__":
    main()
