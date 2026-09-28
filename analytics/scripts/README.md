# Scripts

Reproduce the measurements in `docs/`.

| Script | Reproduces | Runs where |
|---|---|---|
| `translation_audit.py` | [docs/experiments.md §4](../docs/experiments.md) | anywhere — stdlib only |
| `outlet_outlier_check.py` | [docs/experiments.md §3](../docs/experiments.md) | **SLURM GPU** |
| `dedup_impact.py` | [docs/experiments.md §1](../docs/experiments.md) | CPU, needs scikit-learn |

## translation_audit.py

Self-contained. Needs only `ground_news.jsonl`, which the `ground-news/` folder writes to
`data/ground_news/`.

```bash
python scripts/translation_audit.py --data /path/to/data/ground_news/ground_news.jsonl
python scripts/translation_audit.py --data ... --show   # print every match
```

## outlet_outlier_check.py and dedup_impact.py

⚠️ **These two are copies.** They import `config.py` and `splits.py` from the stance
experiment and only run from inside it:

```
muws-allsides-dataset/stance_detection_experiment/
```

They are included here so the method is readable alongside the results. To run them,
copy back into that directory.

```bash
# outlier check — login node has CUDA_VISIBLE_DEVICES=-1, so GPU work needs srun
srun --partition=p_80G --gres=gpu:h100:1 \
  bash -lc 'conda activate rag && HF_HUB_OFFLINE=1 python outlet_outlier_check.py --cap 250'

# deduplication impact — CPU only
conda activate rag && python dedup_impact.py
```

`outlet_outlier_check.py` appends to its output file and skips `article_id`s already
present, so an interrupted run resumes.
