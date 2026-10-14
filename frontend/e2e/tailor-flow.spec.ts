import { expect, test, type Route } from "@playwright/test";
import path from "node:path";

const API = "http://localhost:8000";
const JD = "We are hiring a Backend Software Engineer to build and scale REST APIs in Node.js and TypeScript. "
  + "You will own services end to end, work with PostgreSQL and AWS, and collaborate with product and design. ".repeat(2);

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

// The LLM key isn't configured locally, so the three LLM-backed endpoints are stubbed.
// Signup, upload, JD save and export all hit the real backend.
test("sign up, upload CV, add JD, tailor, accept and export DOCX", async ({ page }) => {
  const match = {
    score: 72, covered: 2, weak: 1, gaps: 1,
    items: [
      { requirement: "Node.js", kind: "must", status: "covered", evidence: "Node.js, TypeScript, React" },
      { requirement: "TypeScript", kind: "must", status: "covered", evidence: "Node.js, TypeScript, React" },
      { requirement: "AWS", kind: "must", status: "weak", evidence: null },
      { requirement: "Kubernetes", kind: "nice", status: "gap", evidence: null },
    ],
  };
  let editBlockId = "";
  const edits = () => [{
    block_id: editBlockId, new_text: "Built REST APIs in Node.js and TypeScript for the order service handling 2M requests/day.",
    rationale: "Mentions the stack the role asks for.", added_keywords: ["Node.js", "TypeScript"],
  }];

  await page.route(`${API}/v1/jds/*/analysis`, (r) => json(r, {
    jd_id: "x", cached: false, role_title: "Backend Software Engineer", seniority: "mid",
    required_skills: ["Node.js", "TypeScript", "AWS"], nice_to_haves: ["Kubernetes"],
    responsibilities: ["Build REST APIs"], ats_keywords: ["REST", "PostgreSQL"],
  }));
  await page.route(`${API}/v1/matches`, (r) => json(r, { cv_id: "x", jd_id: "x", ...match }));
  await page.route(`${API}/v1/tailoring`, async (r) => {
    const { cv_id } = r.request().postDataJSON();
    const cv = await (await page.request.get(`${API}/v1/cvs/${cv_id}`, { headers: { authorization: r.request().headers()["authorization"] } })).json();
    editBlockId = cv.blocks.find((b: { type: string }) => b.type === "bullet").id;
    await json(r, { job_id: "job1", status: "queued", step: "", steps: [], error: null, result: null }, 202);
  });
  await page.route(`${API}/v1/tailoring/job1`, (r) => json(r, {
    job_id: "job1", status: "done", step: "done", steps: [], error: null,
    result: { match, edits: edits(), dropped: [{ block_id: "gone", reason: "Invented a number" }] },
  }));

  // Sign up
  await page.goto("/");
  await page.getByRole("button", { name: /sign up|get started/i }).first().click();
  await page.getByLabel("Email").fill(`e2e-${Date.now()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("button", { name: /log out/i })).toBeVisible();

  // Upload CV
  await page.goto("/#/tailor");
  await page.locator('input[type="file"]').setInputFiles(path.join(import.meta.dirname, "fixtures", "cv.docx"));
  await expect(page.getByText("cv.docx").first()).toBeVisible();
  await page.getByRole("button", { name: "Add a job" }).click();

  // Add JD and analyse
  await page.getByLabel("Job description").fill(JD);
  await page.getByRole("button", { name: "Analyse this role" }).click();
  await page.getByRole("button", { name: "See how your CV matches" }).click();

  // Match, then tailor
  await expect(page.getByText("Kubernetes").first()).toBeVisible();
  await page.getByRole("button", { name: "Tailor my CV" }).click();

  // Review: accept the single change
  await expect(page.getByText("Needs your decision")).toBeVisible();
  await page.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(page.getByText("Accepted", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Continue to export" }).click();

  // Export the real DOCX
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download DOCX" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.docx$/);
});

test("login rejects a wrong password", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /log in/i }).first().click();
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByLabel("Password", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: /^log in$/i }).click();
  await expect(page.getByText(/couldn't|failed|invalid|incorrect/i).first()).toBeVisible();
});
