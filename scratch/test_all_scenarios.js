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

async function testScenario(topic, wrongAnswer, correctAnswer, partialAnswer) {
  console.log(`\n--------------------------------------------------`);
  console.log(`Testing Topic: "${topic}"`);
  console.log(`--------------------------------------------------`);

  const repo = new LocalSessionRepository();

  // 1. Create session
  const session = await repo.createSession(topic);
  assert.strictEqual(session.topic, topic);
  assert(session.messages[0].content.includes(topic), `Initial question must mention "${topic}"`);
  console.log(`✓ Created session for "${topic}" (id=${session.sessionId})`);

  // 2. Completely wrong answer -> Teacher Mode
  const turnWrong = await repo.sendMessage(session.sessionId, wrongAnswer);
  assert.strictEqual(turnWrong.decision.next_mode, "TEACHER", `Wrong answer should trigger TEACHER mode for "${topic}"`);
  assert(turnWrong.ai_message.content.includes("Verification"), `Teacher response must have verification question for "${topic}"`);
  console.log(`✓ Wrong answer correctly triggered Teacher Mode: "${wrongAnswer}"`);

  // 3. Correct verification answer -> Back to Student Mode
  const turnCorrect = await repo.sendMessage(session.sessionId, correctAnswer);
  assert.strictEqual(turnCorrect.decision.next_mode, "STUDENT", `Correct verification should return to STUDENT mode for "${topic}"`);
  assert.strictEqual(turnCorrect.decision.should_restore_interrupted_question, true);
  console.log(`✓ Correct verification returned to Student Mode and restored question`);

  // 4. Partial answer -> Student Mode Probing
  const turnPartial = await repo.sendMessage(session.sessionId, partialAnswer);
  assert.strictEqual(turnPartial.decision.next_mode, "STUDENT", `Partial answer should stay in STUDENT mode for "${topic}"`);
  assert(turnPartial.decision.strategy.startsWith("PROBE_"), `Should probe reasoning for "${topic}"`);
  console.log(`✓ Partial answer probed reasoning in Student Mode: strategy=${turnPartial.decision.strategy}`);

  // 5. Restore session from repository (simulate browser refresh)
  const restored = await repo.getSession(session.sessionId);
  assert.strictEqual(restored.topic, topic);
  assert.strictEqual(restored.currentMode, "STUDENT");
  assert.strictEqual(restored.messages.length, 7, `Expected 7 messages in history for "${topic}"`);
  console.log(`✓ Session for "${topic}" successfully survived reload with full history intact`);
}

async function runAll() {
  console.log("==================================================");
  console.log("VERIFYING 5 END-TO-END CURIO TOPIC SCENARIOS");
  console.log("==================================================");

  // Scenario 1: Photosynthesis
  await testScenario(
    "Photosynthesis",
    "Plants eat sunlight and turn it directly into oxygen.",
    "Light energy is converted into chemical energy stored in ATP and NADPH.",
    "Because sunlight provides food and sugar for the plant."
  );

  // Scenario 2: Binary Search
  await testScenario(
    "Binary Search",
    "Because binary search checks every element one by one.",
    "Because the array is sorted, comparing with the middle element lets us eliminate the entire right half if target is smaller.",
    "Because otherwise we can't find the value efficiently."
  );

  // Scenario 3: Operating Systems
  await testScenario(
    "Operating Systems",
    "The CPU stores all files permanently and memory never erases.",
    "The operating system manages hardware abstraction, process scheduling, and memory protection.",
    "An OS manages files and runs programs for the user."
  );

  // Scenario 4: Python decorators
  await testScenario(
    "Python decorators",
    "A decorator is a CSS style that changes the color of Python code.",
    "A decorator is a higher-order function that takes another function as an argument and extends its behavior without modifying it.",
    "It wraps a function to add extra stuff before and after."
  );

  // Scenario 5: TCP congestion control
  await testScenario(
    "TCP congestion control",
    "TCP never drops packets and sends at infinite speed unconditionally.",
    "TCP uses slow start, congestion avoidance, and multiplicative decrease based on packet loss or delay to prevent network collapse.",
    "It slows down when there are too many packets in the network."
  );

  console.log("\n==================================================");
  console.log("ALL 5 TOPIC SCENARIOS VERIFIED AND PASSED! 🎯");
  console.log("==================================================");
}

runAll().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
