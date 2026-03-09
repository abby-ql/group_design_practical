# External dataset options (open / research-friendly) — with caveats

This sponsor pack ships **synthetic** Items so teams can run offline without needing platform keys.

If you want a larger “real text” corpus, here are common options:

## A) Wikipedia talk-page comments (toxicity labels)
- Commonly used in the Jigsaw Toxic Comment Classification Challenge.
- Good for demonstrating: toxicity, sentiment, quoting, sarcasm markers, etc.
- Caveat: although some redistributions are labeled “CC0”, the underlying comment text is generally sourced from Wikipedia and governed by Creative Commons **Attribution‑ShareAlike** terms — verify license and attribution requirements.

Suggested sources:
- Hugging Face dataset: `thesofakillers/jigsaw-toxic-comment-classification-challenge`
- TensorFlow Datasets mirror: `wikipedia_toxicity_subtypes`

## B) Stack Exchange / Stack Overflow data dump
- Posts and comments with permissive Creative Commons terms (BY‑SA).
- Huge corpus; you can sample small subsets for this project.
- Good for “professional context” examples (job search / hiring).

## C) Twitter/X datasets
Most academic Twitter/X datasets are shared as **Tweet IDs** (and sometimes User IDs) only. To access full text, you typically need to **rehydrate** IDs using the API, and you must comply with deletion/compliance rules.

For this student project (no OAuth apps; keys may be unavailable), we recommend:
- Use the synthetic Items in this sponsor pack, OR
- Use an open-licensed corpus (A or B), OR
- If you do have an API key, use an ID-only corpus + hydration tooling.

Helpful references:
- “Twitter Data Curation Primer” (Data Curation Network) — explains ID hydration
- University guidance documents often describe the “Tweet IDs only” sharing norm
