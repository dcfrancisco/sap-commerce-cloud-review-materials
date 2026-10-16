import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (error) {
  throw new Error("Browser E2E requires Playwright. Set NODE_PATH to a project-installed Playwright module before running scripts/browser_e2e.mjs.");
}

const baseUrl = process.env.ACADEMY_BASE_URL || "http://127.0.0.1:8000";
const browser = await chromium.launch({headless:true, executablePath:process.env.ACADEMY_CHROME_PATH || undefined});
const page = await browser.newPage();
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const click = async (selector) => { const target = page.locator(selector); assert(await target.count() === 1, `expected one ${selector}`); await target.click(); };
const choose = async (selector, value) => { const target = page.locator(selector); assert(await target.count() === 1, `expected one ${selector}`); await target.selectOption(value); };
const output = () => page.locator("#opsOut").innerText();

try {
  await page.goto(baseUrl, {waitUntil:"domcontentloaded"});
  const scenarioOptions = page.locator("#opsScenario option");
  assert(await scenarioOptions.count() > 0, "scenario catalog did not load");
  await scenarioOptions.nth(0).waitFor({state:"attached", timeout:5000});
  await choose("#opsScenario", "OPS-INC-002");
  await click("#opsStart");
  assert((await output()).includes("Checkout Latency"), "incident selection did not start");

  await choose("#opsMode", "examination");
  await page.locator("#opsMessage").fill("What should I investigate next?");
  await click("#opsCoach");
  const coaching = await output();
  assert(coaching.includes("examination-coaching"), "examination mode was not preserved");
  assert(coaching.includes("revealedEvidenceCount"), "coach did not receive incident context");

  for (const investigation of ["inspect-service-sli","inspect-change-events","inspect-jvm-workers","inspect-db-pool","inspect-service-flow","inspect-custom-job","inspect-transaction-integrity","inspect-log-correlation"]) {
    await choose("#opsInvestigation", investigation);
    await click("#opsInvestigate");
  }
  for (const action of ["declare-incident","pause-custom-export","protect-checkout-traffic"]) {
    await choose("#opsAction", action);
    await click("#opsAct");
  }

  await page.reload({waitUntil:"domcontentloaded"});
  await page.locator("#opsResume").waitFor({state:"attached", timeout:5000});
  await click("#opsResume");
  assert((await output()).includes("inspect-log-correlation"), "persisted investigation state did not resume");

  await choose("#opsAction", "validate-performance-recovery");
  await click("#opsAct");
  const reasoning = {
    hypothesis:{primaryCauseCategory:"jdbc-pool-contention-from-custom-workload",statement:"The customer export consumes shared database capacity and makes checkout wait.",supportingEvidence:["inspect-service-sli","inspect-db-pool","inspect-service-flow","inspect-custom-job"],rejectedAlternatives:[{category:"jvm-memory",reason:"Heap and GC do not lead the incident.",evidence:["inspect-jvm-workers"]},{category:"traffic-spike",reason:"Traffic remains near baseline.",evidence:["inspect-service-sli"]}]},
    containment:{actionId:"pause-custom-export",rationale:"Stop the evidenced customer-owned workload after declaring command.",riskAccepted:"Export is delayed but checkout capacity is protected.",rollbackPlan:"Re-enable only after bounded concurrency tests pass."},
    recovery:{actionId:"pause-custom-export",rationale:"Allow pool usage and waiting requests to drain.",residualRisk:"Three payment outcomes remain ambiguous."},
    verification:[{check:"pool",evidence:["inspect-db-pool"],expected:"pool wait returns to baseline",observed:"synthetic recovery rule passes"},{check:"checkout",evidence:["inspect-service-sli"],expected:"p95 and errors recover",observed:"synthetic checkout checks pass"},{check:"integrity",evidence:["inspect-transaction-integrity"],expected:"exceptions are reconciled",observed:"three exceptions are controlled"}],
    prevention:[{control:"bounded export concurrency",owner:"commerce engineering",measure:"pool headroom under checkout load"},{control:"overlap alert",owner:"operations",measure:"alert before checkout SLO burn"}],
    communication:{impact:"checkout degraded",timeline:"18:02 to recovery",owner:"incident commander",nextUpdate:"every 15 minutes"}
  };
  await page.locator("#opsMessage").fill(JSON.stringify(reasoning));
  await click("#opsConclude");
  const conclusion = await output();
  assert(conclusion.includes('"passed": true'), "structured conclusion did not pass");
  assert(conclusion.includes("competencyScores"), "competency feedback was not returned");
  console.log(JSON.stringify({status:"PASS", journey:["select","investigate","coach","act","reload-resume","conclude"], baseUrl}, null, 2));
} finally {
  await browser.close();
}
