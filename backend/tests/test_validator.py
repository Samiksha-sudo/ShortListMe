import pytest

from app.schemas.cv import ParsedCV
from app.schemas.jd import JDAnalysisResult
from app.schemas.rewrite import ModelEdits, ProposedEdit
from app.services import llm, rewriting, validator
from app.services.parsing.docx_parser import parse_docx
from tests import samples

REST = "Built REST APIs for the order service handling 2M requests/day."
REACT = "Developed React dashboards used by 300 support agents."
JD = JDAnalysisResult(role_title="Backend Engineer", seniority="mid", required_skills=["PostgreSQL"],
                      ats_keywords=["PostgreSQL"])


@pytest.fixture(scope="module")
def cv() -> ParsedCV:
    return parse_docx(samples.single_column(), "cv1", "cv.docx")


def block(cv, text):
    return next(b for b in cv.blocks if b.text == text)


def check(cv, original, new):
    return validator.check_edit(cv, block(cv, original), new)


def test_clean_rewording_passes(cv):
    assert check(cv, REACT, "Built React dashboards used by 300 support agents.") == []


def test_new_number_is_rejected(cv):
    errors = check(cv, REST, "Built REST APIs for the order service handling 5M requests/day.")
    assert any("New numbers" in e and "5" in e for e in errors)


def test_number_already_in_the_block_is_allowed(cv):
    assert check(cv, REST, "Built REST APIs for the order service serving 2M requests/day.") == []


def test_unknown_company_or_tool_is_rejected(cv):
    errors = check(cv, REACT, "Developed Kubernetes dashboards used by 300 support agents.")
    assert any("kubernetes" in e for e in errors)


def test_tool_from_elsewhere_in_the_cv_is_allowed(cv):
    assert check(cv, REACT, "Developed PostgreSQL dashboards used by 300 support agents.") == []


def test_headline_seniority_change_is_rejected(cv):
    errors = check(cv, "Backend Software Engineer", "Backend Software Engineer, Senior")
    assert any("seniority" in e for e in errors)


def test_headline_must_start_from_original(cv):
    errors = check(cv, "Backend Software Engineer", "Software Engineer, Backend")
    assert any("start from the original" in e for e in errors)


def test_locked_block_is_rejected(cv):
    errors = check(cv, "Jane Doe", "Jane Q Doe")
    assert errors == ["This block is locked and cannot be edited."]


def test_unknown_block_is_rejected(cv):
    assert validator.check_edit(cv, None, "anything") == ["Not a block in this CV."]


def test_over_length_edit_is_rejected(cv):
    assert any("15%" in e for e in check(cv, REACT, REACT + " and many other things as well"))


def fake_llm(monkeypatch, rounds):
    prompts = []

    def fake(prompt, schema, system=None, temperature=0.0):
        prompts.append(prompt)
        return ModelEdits(edits=rounds[min(len(prompts), len(rounds)) - 1])

    monkeypatch.setattr(llm, "generate_model", fake)
    return prompts


def edit(cv, original, new):
    return ProposedEdit(block_id=block(cv, original).id, new_text=new, rationale="Fits the JD.")


def test_rejected_edit_is_retried_once_with_the_error_then_accepted(cv, monkeypatch):
    bad = edit(cv, REACT, "Developed Kubernetes dashboards used by 300 support agents.")
    good = edit(cv, REACT, "Built React dashboards used by 300 support agents.")
    prompts = fake_llm(monkeypatch, [[bad], [good]])
    kept, dropped = rewriting.propose(cv, JD)
    assert [e.new_text for e in kept] == [good.new_text] and dropped == []
    assert len(prompts) == 2 and "kubernetes" in prompts[1]


def test_edit_still_invalid_after_retry_is_dropped(cv, monkeypatch):
    bad = edit(cv, REACT, "Developed Kubernetes dashboards used by 300 support agents.")
    prompts = fake_llm(monkeypatch, [[bad], [bad]])
    kept, dropped = rewriting.propose(cv, JD)
    assert kept == [] and len(dropped) == 1 and "kubernetes" in dropped[0].reason
    assert len(prompts) == 2  # retried exactly once


def test_retry_that_omits_the_block_drops_it(cv, monkeypatch):
    bad = edit(cv, REACT, "Developed Kubernetes dashboards used by 300 support agents.")
    fake_llm(monkeypatch, [[bad], []])
    kept, dropped = rewriting.propose(cv, JD)
    assert kept == [] and len(dropped) == 1


def test_valid_edits_do_not_trigger_a_retry(cv, monkeypatch):
    good = edit(cv, REACT, "Built React dashboards used by 300 support agents.")
    prompts = fake_llm(monkeypatch, [[good]])
    kept, _ = rewriting.propose(cv, JD)
    assert len(kept) == 1 and len(prompts) == 1
