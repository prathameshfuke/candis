# Redrob Candidate Discovery Ranker

CPU-only rule-based ranker for the Senior AI Engineer candidate discovery task.

## Run

```bash
python rank.py --candidates ".\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl" --out submission.csv
python ".\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\validate_submission.py" submission.csv
```

## Approach

The ranker streams JSONL candidates, extracts trust-weighted skill groups, analyzes career trajectory, penalizes honeypots, and multiplies the technical fit by platform availability.

Important safeguards:

- Keyword-stuffing skills are discounted when marked expert with no duration or endorsements.
- Honeypots are detected from timeline conflicts, inflated experience, and suspicious expert-skill patterns.
- Non-ML titles and consulting-only careers are strong career penalties.
- Platform activity, response rate, notice period, interview completion, and GitHub activity act as a multiplier.
- Scores are emitted in strictly decreasing order to satisfy CSV validation.
