import pytest

from app.schemas.jd import JDAnalysisResult
from app.schemas.match import Judgement, Judgements, MatchItem
from app.services import llm, matching
from tests import samples
from tests.test_jd import JD, create
from tests.test_upload_cv import post

ANALYSIS = {"role_title": "Backend Engineer", "seniority": "mid",
            "required_skills": ["PostgreSQL", "REST APIs", "Python"], "nice_to_haves": ["Kubernetes"],
            "responsibilities": [], "ats_keywords": []}

# Judgements by 1-based requirement index: PostgreSQL, REST APIs, Python, Kubernetes
ANSWER = [
    Judgement(index=1, status="covered", evidence="Node.js, TypeScript, React, PostgreSQL, Docker, AWS"),
    Judgement(index=2, status="covered", evidence="Built REST APIs for the order service handling 2M requests/day."),
    Judgement(index=3, status="gap"),
    Judgement(index=4, status="weak", evidence="Worked on the deployment pipeline to speed up releases."),
]


@pytest.fixture
def setup(client, monkeypatch):
    cv_id = post(client, "cv.docx", samples.single_column()).json()["cv_id"]
    jd_id = create(client, JD).json()["jd_id"]
    prompts = []

    def fake(prompt, schema, system=None, temperature=0.0):
        if schema is JDAnalysisResult:
            return schema.model_validate(ANALYSIS)
        prompts.append(prompt)
        return Judgements(items=fake.answer)

    fake.answer = list(ANSWER)
    monkeypatch.setattr(llm, "generate_model", fake)
    return client, cv_id, jd_id, fake, prompts


def run(client, cv_id, jd_id):
    return client.post("/v1/matches", json={"cv_id": cv_id, "jd_id": jd_id})


def test_marks_each_requirement_covered_weak_or_gap(setup):
    client, cv_id, jd_id, *_ = setup
    body = run(client, cv_id, jd_id).json()
    status = {i["requirement"]: i["status"] for i in body["items"]}
    assert status == {"PostgreSQL": "covered", "REST APIs": "covered", "Python": "gap", "Kubernetes": "weak"}
    assert (body["covered"], body["weak"], body["gaps"]) == (2, 1, 1)


def test_must_haves_count_double_in_score(setup):
    client, cv_id, jd_id, *_ = setup
    # weights: PostgreSQL 2 + REST 2 + Python 2 + Kubernetes 1 = 7; earned 2 + 2 + 0 + 0.5 = 4.5 -> 64
    assert run(client, cv_id, jd_id).json()["score"] == 64


def test_score_weighting_directly():
    must_gap = [MatchItem(requirement="a", kind="must", status="gap"), MatchItem(requirement="b", kind="nice", status="covered")]
    nice_gap = [MatchItem(requirement="a", kind="must", status="covered"), MatchItem(requirement="b", kind="nice", status="gap")]
    assert matching.score(must_gap) == 33 and matching.score(nice_gap) == 67
    assert matching.score([]) == 0


def test_covered_without_a_real_quote_is_downgraded_to_weak(setup):
    client, cv_id, jd_id, fake, _ = setup
    fake.answer[0] = Judgement(index=1, status="covered", evidence="Ten years of PostgreSQL tuning")  # not in CV
    item = next(i for i in run(client, cv_id, jd_id).json()["items"] if i["requirement"] == "PostgreSQL")
    assert item["status"] == "weak" and item["evidence"] is None


def test_gaps_never_carry_evidence(setup):
    client, cv_id, jd_id, fake, _ = setup
    fake.answer[2] = Judgement(index=3, status="gap", evidence="Node.js, TypeScript")
    item = next(i for i in run(client, cv_id, jd_id).json()["items"] if i["requirement"] == "Python")
    assert item["status"] == "gap" and item["evidence"] is None


def test_matching_does_not_change_the_cv(setup):
    client, cv_id, jd_id, *_ = setup
    before = client.get(f"/v1/cvs/{cv_id}").json()
    run(client, cv_id, jd_id)
    assert client.get(f"/v1/cvs/{cv_id}").json() == before


def test_prompt_marks_cv_as_untrusted(setup):
    client, cv_id, jd_id, _, prompts = setup
    run(client, cv_id, jd_id)
    assert "<cv>" in prompts[0] and "Jane Doe" in prompts[0] and "3. Python" in prompts[0]


def test_incomplete_judgements_are_rejected_as_malformed(setup):
    client, cv_id, jd_id, fake, _ = setup
    fake.answer = fake.answer[:2]
    res = run(client, cv_id, jd_id)
    assert res.status_code == 502 and "malformed" in res.json()["detail"]


def test_unknown_cv_or_jd_is_404(setup):
    client, cv_id, jd_id, *_ = setup
    assert run(client, "nope", jd_id).status_code == 404
    assert run(client, cv_id, "nope").status_code == 404
