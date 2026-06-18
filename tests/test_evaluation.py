"""The eval harness should pass offline against the deterministic tutor."""

from backend.evaluation import run_offline


def test_retrieval_and_grading_suites_pass_offline():
    report = run_offline()
    assert report["passed"] is True, report
    assert report["suites"]["retrieval"]["mean_score"] == 1.0
    assert report["suites"]["grading"]["mean_score"] == 1.0


def test_offline_report_shape():
    report = run_offline(["retrieval"])
    assert set(report["suites"]) == {"retrieval"}
    assert report["suites"]["retrieval"]["n"] >= 3
