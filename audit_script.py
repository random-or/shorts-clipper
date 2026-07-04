import logging
import time
from copy import deepcopy
from shorts_clipper.core.models import TranscriptSegment, TranscriptWord
from shorts_clipper.attention.engine import SimulationEngine, AttentionEngine
from shorts_clipper.attention.models import CounterfactualVariant

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("IVV_Audit")

sim_engine = SimulationEngine()
attention_engine = AttentionEngine()

def run_stress_tests():
    log.info("--- RUNNING STRESS TESTS ---")
    
    cases = {
        "Empty": [],
        "Single Word": [TranscriptSegment(start=0.0, end=1.0, text="Word", words=[])],
        "Broken Timestamps": [TranscriptSegment(start=5.0, end=2.0, text="Backward time", words=[])],
        "Negative Timestamps": [TranscriptSegment(start=-1.0, end=0.0, text="Negative", words=[])],
        "Heavy Silence": [
            TranscriptSegment(start=0.0, end=1.0, text="Hello", words=[]),
            TranscriptSegment(start=10.0, end=11.0, text="World", words=[])
        ],
        "Extreme Repetition": [TranscriptSegment(start=0.0, end=1.0, text="yes "*100, words=[])],
        "Unicode/Emoji": [TranscriptSegment(start=0.0, end=1.0, text="Hello 🌍🔥", words=[])],
    }
    
    for name, segments in cases.items():
        try:
            res = sim_engine.optimize_clip(segments)
            log.info(f"Stress {name}: PASS. Winner: {res.winner_id if res else 'None'}")
        except Exception as e:
            log.error(f"Stress {name}: FAIL. Error: {e}")

def run_ablation():
    log.info("--- RUNNING JUDGE ABLATION ---")
    clip = [
        TranscriptSegment(start=0.0, end=1.0, text="You won't believe this secret trick!", words=[]),
        TranscriptSegment(start=1.1, end=2.0, text="It makes $1000 a day.", words=[])
    ]
    
    # Evaluate full
    base_variant = CounterfactualVariant(
        variant_id="base", description="base", start_time=0.0, end_time=2.0, modified_segments=clip
    )
    full_report = attention_engine.evaluate_variant(base_variant)
    
    judges_backup = dict(attention_engine.judges)
    
    for judge_name in judges_backup.keys():
        attention_engine.judges.pop(judge_name)
        try:
            ablated_report = attention_engine.evaluate_variant(base_variant)
            score_diff = abs(full_report.scroll_stop_prob - ablated_report.scroll_stop_prob) + \
                         abs(full_report.completion_prob - ablated_report.completion_prob) + \
                         abs(full_report.shareability - ablated_report.shareability) + \
                         abs(full_report.memorability - ablated_report.memorability)
                         
            if score_diff < 0.01:
                log.warning(f"Judge '{judge_name}' ABLATION FAILED: No significant impact on final scores (diff={score_diff}). Redundant?")
            else:
                log.info(f"Judge '{judge_name}' Ablation: PASS (Impact: {score_diff:.3f})")
        finally:
            attention_engine.judges[judge_name] = judges_backup[judge_name]

def test_behavioral_optimization():
    log.info("--- RUNNING BEHAVIORAL OPTIMIZATION ---")
    clip = [
        TranscriptSegment(start=0.0, end=1.5, text="Um... hello... guys.", words=[]),
        TranscriptSegment(start=1.6, end=3.0, text="Welcome back.", words=[]),
        TranscriptSegment(start=4.0, end=5.0, text="You won't believe this secret trick!", words=[]), # The hook after 1s dead air
        TranscriptSegment(start=5.1, end=6.0, text="It makes $1000 a day.", words=[])
    ]
    
    res = sim_engine.optimize_clip(clip)
    
    base_report = res.reports["base"]
    winner_report = res.reports[res.winner_id]
    
    log.info(f"Optimal Variant Chosen: {res.winner_id}")
    log.info(f"Base Completion Prob: {base_report.completion_prob:.3f}")
    log.info(f"Winner Completion Prob: {winner_report.completion_prob:.3f}")
    
    if winner_report.completion_prob > base_report.completion_prob:
        log.info("Behavioral Optimization: PASS")
    else:
        log.error("Behavioral Optimization: FAIL")

if __name__ == "__main__":
    run_stress_tests()
    run_ablation()
    test_behavioral_optimization()
