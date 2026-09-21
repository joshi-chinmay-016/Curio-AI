/**
 * Automated Verification of the Exact Video Scenario (FastAPI)
 * Tests LocalSessionRepository state transitions, multi-turn Teacher Mode,
 * non-answer rejections, and evidence-based verification pass.
 */
const assert = require("assert");

// Mock window.localStorage
const storageMap = new Map();
global.window = {
  localStorage: {
    getItem: (key) => storageMap.get(key) || null,
    setItem: (key, val) => storageMap.set(key, String(val)),
    removeItem: (key) => storageMap.delete(key),
    clear: () => storageMap.clear(),
  },
};

const { LocalSessionRepository } = require("./local_repo_test_shim.js");

async function testFastAPIVideoScenario() {
  console.log("==================================================");
  console.log("TESTING EXACT FASTAPI VIDEO SCENARIO");
  console.log("==================================================");

  const repo = new LocalSessionRepository();

  // STEP 1: Create Session for FastAPI
  console.log("\n[Step 1] Creating session for 'FastAPI'...");
  const session = await repo.createSession("FastAPI");
  assert.strictEqual(session.topic, "FastAPI");
  assert.strictEqual(session.currentMode, "STUDENT");
  console.log("✓ Session initialized in STUDENT mode.");
  console.log("Curio:", session.messages[0].content.split("\n")[0]);

  // STEP 2: Learner says "I don't know about the mechanism. can you teach me?"
  console.log("\n[Step 2] Learner: 'I don't know about the mechanism. can you teach me?'");
  const turn1 = await repo.sendMessage(session.sessionId, "I don't know about the mechanism. can you teach me?");
  
  assert.strictEqual(turn1.decision.next_mode, "TEACHER", "Must transition to TEACHER mode on explicit teach request");
  assert.strictEqual(turn1.decision.strategy, "TEACH_GAP");
  assert.strictEqual(turn1.decision.should_restore_interrupted_question, false);
  assert(turn1.ai_message.content.includes("ASGI"), "Teacher explanation must explain ASGI / Uvicorn mechanism");
  assert(turn1.ai_message.content.includes("Verification:"), "Must include verification question");
  console.log("✓ Transitioned from STUDENT -> TEACHER mode.");
  console.log("Curio response:\n", turn1.ai_message.content);

  // STEP 3: Learner says "ok teach me about the mechanism" during Teacher Mode
  // CRITICAL: This is what was WRONG in the video (falsely passed verification)
  console.log("\n[Step 3] Learner in Teacher Mode: 'ok teach me about the mechanism'");
  const turn2 = await repo.sendMessage(session.sessionId, "ok teach me about the mechanism");

  assert.strictEqual(turn2.decision.next_mode, "TEACHER", "Must REMAINS in TEACHER mode!");
  assert.strictEqual(turn2.decision.should_restore_interrupted_question, false, "Must NOT restore question!");
  assert(!turn2.ai_message.content.includes("CONCEPT VERIFIED"), "Must NOT declare concept verified!");
  assert(!turn2.ai_message.content.includes("continue where we left off"), "Must NOT restore Student inquiry yet!");
  console.log("✓ Correctly remained in TEACHER mode (did NOT falsely verify concept).");
  console.log("Curio response:\n", turn2.ai_message.content);

  // STEP 4: Learner says generic "yes"
  console.log("\n[Step 4] Learner: 'yes'");
  const turn3 = await repo.sendMessage(session.sessionId, "yes");
  assert.strictEqual(turn3.decision.next_mode, "TEACHER", "Generic 'yes' must NOT exit Teacher Mode");
  assert.strictEqual(turn3.decision.should_restore_interrupted_question, false);
  console.log("✓ Correctly rejected generic 'yes' as verification pass.");
  console.log("Curio response:\n", turn3.ai_message.content);

  // STEP 5: Learner provides partial answer: "Because it handles the requests."
  console.log("\n[Step 5] Learner: 'Because it handles the requests.'");
  const turn4 = await repo.sendMessage(session.sessionId, "Because it handles the requests.");
  assert.strictEqual(turn4.decision.next_mode, "TEACHER", "Partial answer must remain in TEACHER mode");
  assert.strictEqual(turn4.decision.strategy, "PROBE_WHY", "Must probe why/specifics");
  assert.strictEqual(turn4.decision.should_restore_interrupted_question, false);
  assert(turn4.ai_message.content.includes("right track"), "Must acknowledge partial understanding and probe");
  console.log("✓ Correctly probed partial answer in Teacher Mode.");
  console.log("Curio response:\n", turn4.ai_message.content);

  // STEP 6: Learner demonstrates actual understanding:
  // "Because FastAPI is an ASGI application and the server, such as Uvicorn, handles the actual network communication and passes requests to the application."
  console.log("\n[Step 6] Learner: 'Because FastAPI is an ASGI application and the server, such as Uvicorn, handles the actual network communication and passes requests to the application.'");
  const turn5 = await repo.sendMessage(
    session.sessionId,
    "Because FastAPI is an ASGI application and the server, such as Uvicorn, handles the actual network communication and passes requests to the application."
  );

  assert.strictEqual(turn5.decision.next_mode, "STUDENT", "Must transition to STUDENT mode on genuine understanding");
  assert.strictEqual(turn5.decision.should_restore_interrupted_question, true, "Must restore interrupted question");
  assert(turn5.evaluation.mastered_concepts.length > 0, "Concept must be marked as mastered");
  assert(turn5.ai_message.content.includes("continue where we left off") || turn5.ai_message.content.includes("FastAPI"), "Original student question must be restored");
  console.log("✓ Genuine understanding verified! Restored interrupted Student question.");
  console.log("Curio response:\n", turn5.ai_message.content);

  // STEP 7: Verify session persistence
  console.log("\n[Step 7] Checking session persistence after page reload simulation...");
  const persisted = await repo.getSession(session.sessionId);
  assert.strictEqual(persisted.currentMode, "STUDENT");
  assert.strictEqual(persisted.interruptedQuestion, undefined);
  assert.strictEqual(persisted.teacherIntervention.active, false);
  assert.strictEqual(persisted.messages.length, 11); // Initial AI msg + 5 user msgs + 5 AI responses
  console.log("✓ Session persisted with all 11 messages intact.");

  console.log("\n==================================================");
  console.log("ALL FASTAPI VIDEO SCENARIO CHECKS PASSED! 🎉");
  console.log("==================================================");
}

testFastAPIVideoScenario().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
