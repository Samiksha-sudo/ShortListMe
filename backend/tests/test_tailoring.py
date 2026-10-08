import pytest

from app.schemas.jd import JDAnalysisResult
from app.schemas.match import Judgement, Judgements
from app.schemas.rewrite import ModelEdits, ProposedEdit
from app.services import llm
from tests import samples
from tests.test_jd import JD, create
from tests.test_upload_cv import post

ANALYSIS = {"role_title": "Backend Engineer", "seniority": "mid", "required_skills": ["PostgreSQL"],
            "nice_to_haves": [], "responsibilities": [], "ats_keywords": ["PostgreSQL"]}
REACT = "Developed React dashboards used by 300 support agents."


@pytest.fixture
def setup(client, monkeypatch):
    cv_id = post(client, "cv.docx", samples.single_column()).json()["cv_id"]
    jd_id = create(client, JD).json()["jd_id"]
    block_id = next(b["id"] for b in client.get(f"/v1/cvs/{cv_id}").json()["blocks"] if b["text"] == REACT)
    steps = []  # the job's step as seen from inside each LLM call

    def fake(prompt, schema, system=None, temperature=0.0):
        job_id = fake.job_id
        steps.append(client.get(f"/v1/tailoring/{job_id}").json()["step"]) if job_id else None
        if fake.fail:
            raise llm.LLMError("The AI service did not respond. Please try again.")
        if schema is JDAnalysisResult:
            return schema.model_validate(ANALYSIS)
        if schema is Judgements:
            return Judgements(items=[Judgement(index=1, status="gap")])
        return ModelEdits(edits=[ProposedEdit(block_id=block_id, rationale="Fits.",
                                              new_text="Built React dashboards used by 300 support agents.")])

    fake.job_id, fake.fail = None, False
    monkeypatch.setattr(llm, "generate_model", fake)
    return client, cv_id, jd_id, fake, steps


def start(client, cv_id, jd_id):
    return client.post("/v1/tailoring", json={"cv_id": cv_id, "jd_id": jd_id})


def test_start_returns_202_with_job_id(setup):
    client, cv_id, jd_id, *_ = setup
    res = start(client, cv_id, jd_id)
    assert res.status_code == 202
    body = res.json()
    assert body["job_id"] and body["steps"] == ["analysing", "matching", "rewriting"]


def test_pipeline_result_is_stored_and_readable(setup):
    client, cv_id, jd_id, *_ = setup
    job_id = start(client, cv_id, jd_id).json()["job_id"]
    body = client.get(f"/v1/tailoring/{job_id}").json()
    assert body["status"] == "done" and body["step"] == "done" and body["error"] is None
    assert body["result"]["match"]["gaps"] == 1
    assert len(body["result"]["edits"]) == 1 and body["result"]["dropped"] == []


def test_progress_moves_through_each_step(setup, monkeypatch):
    client, cv_id, jd_id, fake, steps = setup
    from app.models import TailoringJob
    from app.services import tailoring

    real_run = tailoring.run

    def run_and_learn_id(job_id, factory):
        fake.job_id = job_id
        real_run(job_id, factory)

    monkeypatch.setattr(tailoring, "run", run_and_learn_id)
    start(client, cv_id, jd_id)
    assert steps == ["analysing", "matching", "rewriting"]


def test_llm_failure_is_stored_as_readable_error(setup):
    client, cv_id, jd_id, fake, _ = setup
    fake.fail = True
    job_id = start(client, cv_id, jd_id).json()["job_id"]
    body = client.get(f"/v1/tailoring/{job_id}").json()
    assert body["status"] == "failed" and body["error"] == "The AI service did not respond. Please try again."
    assert body["result"] is None


def test_unexpected_crash_is_stored_without_leaking_details(setup, monkeypatch):
    client, cv_id, jd_id, *_ = setup
    from app.services import matching

    def boom(*a, **k):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(matching, "match", boom)
    job_id = start(client, cv_id, jd_id).json()["job_id"]
    body = client.get(f"/v1/tailoring/{job_id}").json()
    assert body["status"] == "failed" and "secret" not in body["error"]


def test_unknown_cv_jd_and_job_are_404(setup):
    client, cv_id, jd_id, *_ = setup
    assert start(client, "nope", jd_id).status_code == 404
    assert start(client, cv_id, "nope").status_code == 404
    assert client.get("/v1/tailoring/nope").status_code == 404
