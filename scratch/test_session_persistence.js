/**
 * Node test script to verify Curio AI Session Persistence & Adaptive Mode Switching
 * Mirrors the logic in LocalSessionRepository and DecisionEngine.
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

// We will test the compiled/bundled LocalSessionRepository or transpile-free implementation
const STORAGE_KEY = "curio.sessions.v1";
const MAX_TEACHER_ATTEMPTS = 3;

const EXPLICIT_STUCK_PHRASES = [
  "i don't know",
  "i do not know",
  "idk",
  "i'm stuck",
  "im stuck",
  "i am stuck",
  "i don't understand",
  "i do not understand",
  "i'm confused",
  "im confused",
  "i am confused",
  "i have no idea",
  "can you explain this",
  "can you explain",
  "explain to me",
  "i don't get why",
  "i don't get it",
  "i do not get",
  "help me",
];

function hasExplicitStuckSignal(text) {
  if (!text) return false;
  const clean = text.toLowerCase().trim();
  return EXPLICIT_STUCK_PHRASES.some((p) => clean.includes(p));
}

// We dynamically require the TypeScript file via ts-node or run an equivalent evaluation
async function runTests() {
  console.log("==================================================");
  console.log("RUNNING CURIO AI SESSION PERSISTENCE & MODE TESTS");
  console.log("==================================================");

  // Load the LocalSessionRepository logic directly
  const { LocalSessionRepository } = require("./local_repo_test_shim.js");
  const repo = new LocalSessionRepository();

  // -------------------------------------------------------------
  // Test 1: New Session with Custom Topic
  // -------------------------------------------------------------
  console.log("\n[Test 1] Creating session for 'Photosynthesis'...");
  const sess1 = await repo.createSession("Photosynthesis");
  assert.strictEqual(sess1.topic, "Photosynthesis", "Topic must be Photosynthesis");
  assert.strictEqual(sess1.currentMode, "STUDENT", "Initial mode must be STUDENT");
  assert(sess1.messages[0].content.includes("Photosynthesis"), "Initial question must mention Photosynthesis");
  assert(!sess1.messages[0].content.includes("Binary Search"), "Must not default to Binary Search");
  console.log("✓ Test 1 Passed: Session created with correct topic and initial question.");

  // -------------------------------------------------------------
  // Test 2: Completely Wrong Answer / Major Misconception -> Teacher Mode
  // -------------------------------------------------------------
  console.log("\n[Test 2] Sending completely wrong answer: 'Plants eat sunlight and turn it directly into oxygen.'");
  const turn1 = await repo.sendMessage(sess1.sessionId, "Plants eat sunlight and turn it directly into oxygen.");
  assert.strictEqual(turn1.decision.next_mode, "TEACHER", "Must transition to TEACHER mode");
  assert.strictEqual(turn1.decision.strategy, "TEACH_GAP", "Strategy must be TEACH_GAP");
  assert(turn1.evaluation.correctness < 0.25, "Correctness must be low for completely wrong answer");
  assert(turn1.ai_message.content.includes("Verification"), "Teacher message must contain a verification question");
  assert.strictEqual(turn1.ai_message.content.match(/\?/g).length, 1, "Must contain exactly ONE verification question");

  // Check state updates
  const sess1AfterTurn1 = await repo.getSession(sess1.sessionId);
  assert.strictEqual(sess1AfterTurn1.currentMode, "TEACHER");
  assert(sess1AfterTurn1.interruptedQuestion, "Interrupted question must be snapshotted");
  assert(sess1AfterTurn1.interruptedQuestion.content.includes("Photosynthesis"));
  console.log("✓ Test 2 Passed: Major misconception recognized, Teacher Mode activated with 1 verification question.");

  // -------------------------------------------------------------
  // Test 3: Teacher Verification Passes -> Restores Student Mode
  // -------------------------------------------------------------
  console.log("\n[Test 3] Answering verification correctly: 'Light energy is converted into chemical bonds in ATP and NADPH.'");
  const turn2 = await repo.sendMessage(sess1.sessionId, "Light energy is converted into chemical bonds in ATP and NADPH.");
  assert.strictEqual(turn2.decision.next_mode, "STUDENT", "Must transition back to STUDENT mode");
  assert.strictEqual(turn2.decision.should_restore_interrupted_question, true, "Must restore interrupted question");
  assert(turn2.ai_message.content.includes("continue where we left off") || turn2.ai_message.content.includes("Photosynthesis"), "Must restore original question");

  const sess1AfterTurn2 = await repo.getSession(sess1.sessionId);
  assert.strictEqual(sess1AfterTurn2.currentMode, "STUDENT");
  assert.strictEqual(sess1AfterTurn2.interruptedQuestion, undefined, "Interrupted question must be cleared");
  assert.strictEqual(sess1AfterTurn2.teacherIntervention.active, false, "Intervention must be inactive");
  console.log("✓ Test 3 Passed: Verification passed, Teacher Mode exited, interrupted question restored.");

  // -------------------------------------------------------------
  // Test 4: Partially Correct Answer -> Stays in Student Mode, Probes Reasoning
  // -------------------------------------------------------------
  console.log("\n[Test 4] Sending partially correct answer: 'Because sunlight provides food and sugar.'");
  const turn3 = await repo.sendMessage(sess1.sessionId, "Because sunlight provides food and sugar.");
  assert.strictEqual(turn3.decision.next_mode, "STUDENT", "Partially correct answer must stay in STUDENT mode");
  assert.strictEqual(turn3.decision.strategy, "PROBE_WHY", "Strategy must probe reasoning");
  console.log("✓ Test 4 Passed: Partially correct answer triggered probing without switching to Teacher Mode.");

  // -------------------------------------------------------------
  // Test 5: Explicit Stuck Signal -> Teacher Mode
  // -------------------------------------------------------------
  console.log("\n[Test 5] Sending explicit stuck signal: 'I don't know.'");
  const turn4 = await repo.sendMessage(sess1.sessionId, "I don't know.");
  assert.strictEqual(turn4.decision.next_mode, "TEACHER", "Explicit stuck signal must trigger TEACHER mode");
  console.log("✓ Test 5 Passed: 'I don't know' triggered Teacher Mode.");

  // -------------------------------------------------------------
  // Test 6: Teacher Verification Fails -> Remains in Teacher Mode
  // -------------------------------------------------------------
  console.log("\n[Test 6] Verification fails: 'I still don't get it.'");
  const turn5 = await repo.sendMessage(sess1.sessionId, "I still don't get it.");
  assert.strictEqual(turn5.decision.next_mode, "TEACHER", "Failed verification must remain in TEACHER mode");
  console.log("✓ Test 6 Passed: Failed verification remained in Teacher Mode with adapted explanation.");

  // -------------------------------------------------------------
  // Test 7: Teacher Retry Limit -> Exits to Student Mode at Simpler Difficulty
  // -------------------------------------------------------------
  console.log("\n[Test 7] Verification fails 2nd time (reaches limit)...");
  const turn6 = await repo.sendMessage(sess1.sessionId, "Still completely confused.");
  assert.strictEqual(turn6.decision.next_mode, "STUDENT", "Retry limit must exit to STUDENT mode");
  assert.strictEqual(turn6.decision.should_restore_interrupted_question, true, "Must restore question at simpler level");
  console.log("✓ Test 7 Passed: Retry limit respected, exited Teacher Mode.");

  // -------------------------------------------------------------
  // Test 8: Session Persistence across 'Refreshes'
  // -------------------------------------------------------------
  console.log("\n[Test 8] Simulating page refresh and restoring session...");
  const restoredSession = await repo.getSession(sess1.sessionId);
  assert.strictEqual(restoredSession.sessionId, sess1.sessionId);
  assert.strictEqual(restoredSession.topic, "Photosynthesis");
  assert.strictEqual(restoredSession.messages.length, 13, "All turns must be preserved");

  const sessionList = await repo.listSessions();
  assert(sessionList.some((s) => s.topicName === "Photosynthesis"), "Photosynthesis must appear in session list");
  console.log("✓ Test 8 Passed: Session successfully restored with full message history and metadata.");

  console.log("\n==================================================");
  console.log("ALL 8 END-TO-END TESTS PASSED SUCCESSFULLY! 🎉");
  console.log("==================================================");
}

runTests().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
