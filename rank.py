#!/usr/bin/env python3
"""CPU-only candidate ranker for the Redrob hackathon."""
import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from feature_extractor import extract_all_features
from honeypot_detector import detect_honeypot
from loader import iter_candidates
from scorer import generate_reasoning, score_candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranker")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl or .jsonl.gz")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--top-k", type=int, default=100, help="Number of candidates to output")
    args = parser.parse_args()

    t0 = time.time()
    scored_candidates = []
    honeypot_count = 0

    print(f"[0.0s] Streaming candidates from {args.candidates}...")
    for i, candidate in enumerate(iter_candidates(args.candidates), start=1):
        if i == 1 or i % 10000 == 0:
            print(f"[{time.time() - t0:.1f}s] Processed {i} candidates...")

        is_honeypot, honeypot_reasons = detect_honeypot(candidate)
        honeypot_count += int(is_honeypot)

        features = extract_all_features(candidate)
        scored = score_candidate(features)

        if is_honeypot:
            scored["score"] *= 0.04
        scored["raw_score"] = scored["score"]
        scored["is_honeypot"] = is_honeypot
        scored["honeypot_reasons"] = honeypot_reasons
        scored_candidates.append(scored)

    print(
        f"[{time.time() - t0:.1f}s] Scored {len(scored_candidates)} candidates; "
        f"detected {honeypot_count} honeypots."
    )

    scored_candidates.sort(key=lambda x: (-x["raw_score"], x["candidate_id"]))
    top_k = scored_candidates[: args.top_k]
    honeypots_in_top = sum(1 for c in top_k if c["is_honeypot"])
    print(
        f"[{time.time() - t0:.1f}s] Honeypots in top {args.top_k}: "
        f"{honeypots_in_top}/{len(top_k)}"
    )

    rows = []
    previous_score = None
    top_raw_score = max(top_k[0]["raw_score"], 1e-9) if top_k else 1.0
    for rank, scored in enumerate(top_k, start=1):
        score = round(max(0.0, min(1.0, float(scored["raw_score"]) / top_raw_score)), 6)
        if previous_score is not None and score >= previous_score:
            score = max(0.0, round(previous_score - 0.000001, 6))
        previous_score = score
        rows.append(
            {
                "candidate_id": scored["candidate_id"],
                "rank": rank,
                "score": f"{score:.6f}",
                "reasoning": generate_reasoning(scored),
            }
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        writer.writerows(rows)

    elapsed = time.time() - t0
    print(f"[{elapsed:.1f}s] Done. Written {len(rows)} rows to {out_path}")
    for row in rows[:5]:
        print(
            f"  Rank {row['rank']}: {row['candidate_id']} score={row['score']} | "
            f"{row['reasoning'][:100]}"
        )
    if elapsed > 300:
        print(f"WARNING: elapsed time {elapsed:.0f}s exceeds the 5-minute limit.")


if __name__ == "__main__":
    main()
