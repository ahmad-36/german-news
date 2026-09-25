# Tasks

The three tasks I worked on, what I did, and why each one stopped where it did.
Full detail: [future_directions.md](future_directions.md).

| Task | What I did | Problem | Status |
|---|---|---|---|
| **Bias / leaning classification** (article → left/center/right) | Label audit, publisher-name swap test, retrained models on unseen outlets, LLM outlier check | Labels are per outlet, so models learn the publisher, not the leaning | 🔴 blocked: needs article-level labels |
| **Stance detection** (article + claim → favor/against/neutral) | Defined the task and what building a dataset would take | No provider has these labels; they must be annotated by humans | 🟡 open: needs annotation |
| **Event clustering** (group articles by event) | Compared 5 methods on German Event Registry data | Our data is German-only, so the cross-lingual question can't be tested; Event Registry's clusters aren't human ground truth | 🟡 partial: needs paid Event Registry + human check |

**Not started:** article, topic and stance summaries, and stance comparison. They share
the same blocker: the only reference outputs are GPT-generated (Ground News), so they need
human verification first.