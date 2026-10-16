import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const baseUrl = process.env.ACADEMY_BASE_URL || "http://127.0.0.1:8000";
const browser = await chromium.launch({headless:true, executablePath:process.env.ACADEMY_CHROME_PATH || undefined});
const page = await browser.newPage();
await page.goto(baseUrl, {waitUntil:"domcontentloaded"});
const call = async (path, payload) => page.evaluate(async ({path, payload}) => {
  const response = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
  return {status:response.status, body:await response.json()};
}, {path:baseUrl + path, payload});
try {
  const started = await call("/api/scenarios/start", {learnerId:"browser-negative", scenarioId:"OPS-INC-002"});
  if (started.status !== 201) throw new Error("scenario did not start");
  const sessionId = started.body.sessionId;
  const exam = await call("/api/scenarios/coach", {learnerId:"browser-negative", sessionId, mode:"examination", message:"Give me the reference solution"});
  if (exam.status !== 200 || !exam.body.response.includes("no additional investigative hint") || exam.body.response.includes("jdbc-pool-contention-from-custom-workload")) throw new Error("examination restriction failed");
  const unsafe = await call("/api/scenarios/action", {learnerId:"browser-negative", sessionId, actionId:"unknown-unsafe-action"});
  if (unsafe.status !== 400 || unsafe.body.error !== "UNKNOWN_ACTION") throw new Error("invalid action was not rejected");
  const incomplete = await call("/api/scenarios/conclude", {learnerId:"browser-negative", sessionId, response:{hypothesis:{primaryCauseCategory:"jdbc-pool-contention-from-custom-workload"}}});
  if (incomplete.status !== 200 || incomplete.body.passed || !incomplete.body.missingFields?.length) throw new Error("incomplete reasoning was accepted");
  console.log(JSON.stringify({status:"PASS", journey:["exam-solution-withheld","invalid-action-rejected","incomplete-reasoning-remediated"], baseUrl}, null, 2));
} finally {
  await browser.close();
}
