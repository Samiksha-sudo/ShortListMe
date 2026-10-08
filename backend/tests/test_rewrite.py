import pytest

from app.schemas.jd import JDAnalysisResult
from app.schemas.rewrite import ModelEdits, ProposedEdit
from app.services import llm
from tests import samples
from tests.test_jd import JD, create
from tests.test_upload_cv import post

ANALYSIS = {"role_title": "Backend Engineer", "seniority": "mid",
            "required_skills": ["PostgreSQL", "REST APIs"], "nice_to_haves": [],
            "responsibilities": [], "ats_keywords": ["REST APIs", "PostgreSQL", "CI/CD"]}

REST = "Built REST APIs for the order service handling 2M requests/day."
REACT = "Developed React dashboards used by 300 support agents."


@pytest.fixture
def setup(client, monkeypatch):
    cv_id = post(client, "cv.docx", samples.single_column()).json()["cv_id"]
    jd_id = create(client, JD).json()["jd_id"]
    cv = client.get(f"/v1/cvs/{cv_id}").json()
    blocks = {b["text"]: b for b in cv["blocks"]}

    def fake(prompt, schema, system=None, temperature=0.0):
        if schema is JDAnalysisResult:
            return schema.model_validate(ANALYSIS)
        fake.prompt = prompt
        return ModelEdits(edits=fake.edits)

    fake.edits = []
    monkeypatch.setattr(llm, "generate_model", fake)
    return client, cv_id, jd_id, cv, blocks, fake


def run(client, cv_id, jd_id):
    return client.post("/v1/rewrites", json={"cv_id": cv_id, "jd_id": jd_id})


def edit(block, text, kws=()):
    return ProposedEdit(block_id=block["id"], new_text=text, rationale="Matches the JD.", added_keywords=list(kws))


def test_valid_edit_is_returned_with_fields(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    b = blocks[REST]
    fake.edits = [edit(b, "Built REST APIs on PostgreSQL handling 2M requests/day.", ["PostgreSQL", "REST APIs", "CI/CD"])]
    body = run(client, cv_id, jd_id).json()
    e = body["edits"][0]
    assert e["block_id"] == b["id"] and e["rationale"]
    assert e["added_keywords"] == ["PostgreSQL"]  # REST APIs was already there, CI/CD isn't in the text
    assert body["dropped"] == []


def test_locked_and_unknown_blocks_are_dropped(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    name = blocks["Jane Doe"]
    assert not name["editable"]
    fake.edits = [edit(name, "Jane Q. Doe"), ProposedEdit(block_id="b_999", new_text="x", rationale="r")]
    body = run(client, cv_id, jd_id).json()
    assert body["edits"] == [] and len(body["dropped"]) == 2


def test_prompt_only_lists_editable_blocks(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    run(client, cv_id, jd_id)
    assert "Jane Doe" not in fake.prompt and "jane@example.com" not in fake.prompt
    assert "Built REST APIs" in fake.prompt


def test_length_must_stay_within_15_percent(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    fake.edits = [edit(blocks[REST], REST + " " + "and much more " * 6)]
    body = run(client, cv_id, jd_id).json()
    assert body["edits"] == [] and "15%" in body["dropped"][0]["reason"]


def test_headline_must_start_from_original(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    h = blocks["Backend Software Engineer"]
    assert h["type"] == "headline" and h["editable"]
    fake.edits = [edit(h, "Staff Platform Architect")]
    assert "must start from the original" in run(client, cv_id, jd_id).json()["dropped"][0]["reason"]
    fake.edits = [edit(h, "Backend Software Engineer II")]  # +3 chars, inside the 15% limit
    assert len(run(client, cv_id, jd_id).json()["edits"]) == 1


def test_unchanged_and_duplicate_edits_are_dropped(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    b = blocks[REACT]
    fake.edits = [edit(b, REACT), edit(b, "Built React dashboards used by 300 support agents."),
                  edit(b, "Created React dashboards used by 300 support agents.")]
    body = run(client, cv_id, jd_id).json()
    assert len(body["edits"]) == 1 and len(body["dropped"]) == 2


def test_cv_is_not_modified(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    fake.edits = [edit(blocks[REACT], "Built React dashboards used by 300 support agents.")]
    run(client, cv_id, jd_id)
    assert client.get(f"/v1/cvs/{cv_id}").json() == cv


def test_404_and_502(setup, monkeypatch):
    client, cv_id, jd_id, *_ = setup
    assert run(client, "nope", jd_id).status_code == 404
    assert run(client, cv_id, "nope").status_code == 404

    def boom(*a, **k):
        raise llm.LLMError("The AI service did not respond. Please try again.")

    monkeypatch.setattr(llm, "generate_model", boom)
    assert run(client, cv_id, jd_id).status_code == 502


def test_headline_may_gain_keywords_and_bullets_may_be_trimmed(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    h = blocks["Backend Software Engineer"]
    fake.edits = [edit(h, "Backend Software Engineer | Node.js, AWS", ["Node.js"]),
                  edit(blocks[REST], "Built REST APIs for the order service.")]  # ~30% shorter, no new facts
    body = run(client, cv_id, jd_id).json()
    assert len(body["edits"]) == 2 and body["dropped"] == []


def test_over_trimmed_bullet_is_dropped(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    fake.edits = [edit(blocks[REST], "Built REST APIs.")]
    assert "Shorter" in run(client, cv_id, jd_id).json()["dropped"][0]["reason"]


def test_prompt_tells_model_which_requirements_are_gaps(setup):
    client, cv_id, jd_id, cv, blocks, fake = setup
    run(client, cv_id, jd_id)
    assert "NO evidence" in fake.prompt
