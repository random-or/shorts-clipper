# Scout V2 Production Audit Report

This report documents the root causes, evidence, and proposed minimal fixes for the 4 reported bugs in the Shorts Clipper Scout V2 recommendation and discovery pipeline.

---

## BUG #1: NICHE / KEYWORD NOT REACHING DISCOVERY

### 1. Root Cause
1. **Keyword Bypass / Override**: In the `get_trending_link` function, if channel history is loaded (`known_channels` is not empty), the system limits search queries exclusively to `ytsearch15:from:{kc}` on those channels. The user-provided `keyword` is completely ignored during the discovery stage.
2. **Missing/Incorrect Niche Scoping in History Query**: Originally, the database query to load successful channels did not filter by `niche` (missing `WHERE niche = ?`). As a result, successful channels from other niches (such as Chris Norlund, registered under the `"tech"` niche) were loaded for every search, hijacking the search to irrelevant content. (Note: A partial local fix `WHERE niche = ?` was added, but since `keyword` is still bypassed, the overall bug persists).

### 2. Evidence
- [trending.py:L441-L447](file:///home/random/shorts-clipper/shorts_clipper/scout/trending.py#L441-L447):
  ```python
  elif attempt == 1 and known_channels:
      for kc in known_channels[:2]:
          queries.append(f"ytsearch15:from:{kc}")
  ```
  If `known_channels` is present, it appends only channel queries, completely ignoring the `keyword` parameter.

### 3. Exact Files
- [shorts_clipper/scout/trending.py](file:///home/random/shorts-clipper/shorts_clipper/scout/trending.py)

### 4. Exact Functions
- `get_trending_link`

### 5. Minimal Fix
Modify the query building logic in `get_trending_link` to ensure that if a `keyword` is provided, we prioritize the keyword search instead of bypassing it for channel history:
```python
            known_channels = list(channel_history.keys())
            if channel:
                queries.append(f"ytsearch15:from:{channel}")
            elif attempt == 1 and known_channels and not keyword:
                for kc in known_channels[:2]:
                    queries.append(f"ytsearch15:from:{kc}")
            else:
                if not known_channels and attempt == 1:
                    log.info("No learning data for niche '%s'. Using fresh discovery.", niche)
                queries.extend(build_queries(niche or "tech", keyword))
```

### 6. Risk Level
- **Low**: Ensures that user-specified keywords are respected while preserving the feedback loop when no keywords are provided.

---

## BUG #2: ONLY ONE CANDIDATE EVALUATED

### 1. Root Cause
In the original Scout V2 implementation, the finalist enrichment pool evaluation loop had an early exit `break` statement immediately after finding the first finalist that had English subtitles and passed highlight validation. This prevented subsequent candidates in the pool from being evaluated or compared, contradicting the design specification of comparing up to 5 candidates.

### 2. Evidence
- In the original unmodified loop:
  ```python
  finalists.append(v)
  break  # Single finalist enrichment
  ```
  And the winner selection was simply:
  ```python
  if finalists:
      winner = finalists[0]
  ```

### 3. Exact Files
- [shorts_clipper/scout/trending.py](file:///home/random/shorts-clipper/shorts_clipper/scout/trending.py)

### 4. Exact Functions
- `get_trending_link`

### 5. Minimal Fix
Remove the early `break` and accumulate passing candidates in a list, then sort and select the strongest candidate at the end of the loop (this has been implemented in the active working tree, but needs validation/testing clean-up).

### 6. Risk Level
- **Medium**: Evaluates up to `eval_budget` (5) candidates sequentially, which increases the execution time slightly and adds a few extra Gemini API calls during discovery.

---

## BUG #3: REPORTING INCONSISTENCY

### 1. Root Cause
The variable mapping and logging text are inconsistent. In `trending.py`, the final balanced multi-dimensional score (`final_score`) is stored in `metrics.winner_virality_score`. Then, the pipeline runner (`runner.py`) reads this metric and labels it as "Highest Virality Score", leading to logs claiming a virality score of 94.48 when 94.48 was actually the overall final balanced score.

### 2. Evidence
- [trending.py:L779](file:///home/random/shorts-clipper/shorts_clipper/scout/trending.py#L779):
  ```python
  metrics.winner_virality_score = winner.get("_score", 0.0)
  ```
- [runner.py:L366](file:///home/random/shorts-clipper/shorts_clipper/pipeline/runner.py#L366):
  ```python
  virality = last_m.get("winner_virality_score", 0.0)
  ```
- [runner.py:L385](file:///home/random/shorts-clipper/shorts_clipper/pipeline/runner.py#L385):
  ```python
  f"Reason Winner Was Selected: Highest Virality Score ({virality})\n"
  ```

### 3. Exact Files
- [shorts_clipper/pipeline/runner.py](file:///home/random/shorts-clipper/shorts_clipper/pipeline/runner.py)
- [shorts_clipper/scout/trending.py](file:///home/random/shorts-clipper/shorts_clipper/scout/trending.py)

### 4. Exact Functions
- `run_autopilot` (in `runner.py`)
- `get_trending_link` (in `trending.py`)

### 5. Minimal Fix
Update the label in the autopilot report inside `runner.py` to correctly reflect the final balanced score:
```python
f"Reason Winner Was Selected: Highest Scout V2 Score ({virality})\n"
```

### 6. Risk Level
- **Low**: Clean cosmetic fix to logging output with no structural code impact.

---

## BUG #4: REJECTION METRICS LOOK SUSPICIOUS

### 1. Root Cause
The number of rejected candidates reported in the logs is calculated using a hardcoded formula: `rejected = max(0, video_ids_discovered - 1)`. This gives the false impression that all other 49 discovered videos were evaluated and rejected, when in reality most were filtered out by basic age/views filters or not processed because they exceeded the pool limits.

### 2. Evidence
- [runner.py:L373](file:///home/random/shorts-clipper/shorts_clipper/pipeline/runner.py#L373):
  ```python
  rejected = max(0, last_m.get("video_ids_discovered", 0) - 1)
  ```

### 3. Exact Files
- [shorts_clipper/pipeline/runner.py](file:///home/random/shorts-clipper/shorts_clipper/pipeline/runner.py)

### 4. Exact Functions
- `run_autopilot`

### 5. Minimal Fix
Change the rejected metrics calculation to display real numbers:
- Candidates rejected early by views/age/duration filters: `video_ids_discovered - len(survivors)`
- Candidates evaluated and rejected by the quality check: `rejected_low_quality` (read from `last_m.get("rejected_low_quality", 0)`)
```python
discovered_count = last_m.get("video_ids_discovered", 0)
rejected_low_quality = last_m.get("rejected_low_quality", 0)
# calculate filtered out (e.g. view count, duration, age, cached etc)
filtered_out = max(0, discovered_count - rejected_low_quality - 1)
```
Update the report logs accordingly.

### 6. Risk Level
- **Low**: Simply exposes the correct counters that are already computed by `ScoutMetrics`.
