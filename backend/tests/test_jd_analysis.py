import json

import pytest

from app.services import llm
from tests.test_jd import create

SAMPLES = [
    (
        "Senior Backend Engineer. Build APIs in Python and PostgreSQL, own services end to end and mentor "
        "colleagues. Required: Python, PostgreSQL, REST. Nice to have: Kubernetes.",
        {"role_title": "Senior Backend Engineer", "seniority": "senior",
         "required_skills": ["Python", "PostgreSQL", "REST"], "nice_to_haves": ["Kubernetes"],
         "responsibilities": ["Build APIs", "Own services end to end", "Mentor colleagues"],
         "ats_keywords": ["Python", "PostgreSQL", "REST API", "Kubernetes"]},
    ),
    (
        "Junior Data Analyst wanted to prepare weekly dashboards for the sales team. You must know SQL and "
        "Excel. Tableau experience is a plus. Training provided on the job.",
        {"role_title": "Junior Data Analyst", "seniority": "junior",
         "required_skills": ["SQL", "Excel"], "nice_to_haves": ["Tableau"],
         "responsibilities": ["Prepare weekly dashboards"], "ats_keywords": ["SQL", "Excel", "Tableau"]},
    ),
    (
        "We need a Product Designer to shape our mobile app experience, run user research and hand off "
        "specs to engineers. Figma is essential. Familiarity with design systems is preferred by the team.",
        {"role_title": "Product Designer", "seniority": "unspecified",
         "required_skills": ["Figma"], "nice_to_haves": ["Design systems"],
         "responsibilities": ["Shape mobile app experience", "Run user research", "Hand off specs"],
         "ats_keywords": ["Figma", "design systems", "user research"]},
    ),
]


@pytest.fixture
def mock_llm(monkeypatch):
    calls = []
    answers = {text: ans for text, ans in SAMPLES}

    def fake(prompt, schema, system=None, temperature=0.0):
        calls.append(prompt)
        for text, ans in answers.items():
            if text in prompt:
                return schema.model_validate(ans)
        raise AssertionError("unexpected JD in prompt")

    monkeypatch.setattr(llm, "generate_model", fake)
    return calls


def analyse(client, text):
    jd_id = create(client, text).json()["jd_id"]
    return client.post(f"/v1/jds/{jd_id}/analysis"), jd_id


@pytest.mark.parametrize("text,expected", SAMPLES)
def test_analysis_returns_all_fields(client, mock_llm, text, expected):
    res, jd_id = analyse(client, text)
    assert res.status_code == 200
    body = res.json()
    assert body["jd_id"] == jd_id and body["cached"] is False
    for key, value in expected.items():
        assert body[key] == value


def test_same_text_is_served_from_cache(client, mock_llm):
    text = SAMPLES[0][0]
    first, _ = analyse(client, text)
    second, _ = analyse(client, f"  {text}\r\n")  # different JD row, same normalised hash
    assert first.json()["cached"] is False and second.json()["cached"] is True
    assert len(mock_llm) == 1
    assert {k: v for k, v in first.json().items() if k not in ("jd_id", "cached")} == \
           {k: v for k, v in second.json().items() if k not in ("jd_id", "cached")}


def test_repeat_call_for_same_jd_is_cached(client, mock_llm):
    _, jd_id = analyse(client, SAMPLES[1][0])
    assert client.post(f"/v1/jds/{jd_id}/analysis").json()["cached"] is True
    assert len(mock_llm) == 1


def test_prompt_marks_jd_as_untrusted_data(client, mock_llm):
    analyse(client, SAMPLES[2][0])
    assert "<job_description>" in mock_llm[0] and SAMPLES[2][0] in mock_llm[0]


def test_unknown_jd_is_404(client, mock_llm):
    assert client.post("/v1/jds/nope/analysis").status_code == 404


def test_llm_failure_is_502_and_not_cached(client, monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("The AI service did not respond. Please try again.")

    monkeypatch.setattr(llm, "generate_model", boom)
    res, jd_id = analyse(client, SAMPLES[0][0])
    assert res.status_code == 502 and "did not respond" in res.json()["detail"]

    monkeypatch.setattr(llm, "generate_model", lambda p, s, system=None, temperature=0.0: s.model_validate(SAMPLES[0][1]))
    assert client.post(f"/v1/jds/{jd_id}/analysis").json()["cached"] is False


def test_generate_model_retries_bad_shape_with_error_note(monkeypatch):
    from app.core.config import settings
    from app.schemas.jd import JDAnalysisResult

    monkeypatch.setattr(settings, "gemini_api_key", "k")
    prompts = []
    replies = [json.dumps({"role_title": "X", "seniority": "wizard"}), "not json",
               json.dumps({"role_title": "X", "seniority": "mid"})]

    def fake_request(prompt, system, temperature, json_mode=False):
        prompts.append(prompt)
        return replies[len(prompts) - 1]

    monkeypatch.setattr(llm, "_request", fake_request)
    result = llm.generate_model("p", JDAnalysisResult)
    assert result.seniority == "mid" and len(prompts) == 3
    assert "previous answer was invalid" in prompts[1]


def test_generate_model_gives_up_after_two_retries(monkeypatch):
    from app.schemas.jd import JDAnalysisResult

    monkeypatch.setattr(llm, "_request", lambda *a, **k: "{}")
    with pytest.raises(llm.LLMError, match="malformed"):
        llm.generate_model("p", JDAnalysisResult)
