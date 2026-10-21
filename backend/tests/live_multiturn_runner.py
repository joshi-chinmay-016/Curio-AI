import requests
import json

def run_live_test():
    url = "http://127.0.0.1:8000/api/v1/ai/guest-student-turn"
    topic = "Event Loop in JavaScript"

    print("--- TESTING UNIVERSAL MULTI-TURN FLOW ---")

    # Turn 1: Definition
    data1 = {
        "topic": topic,
        "user_answer": "The event loop is a single-threaded concurrency model in JavaScript that coordinates the execution of code, processing events, and running queued tasks without blocking the main execution thread.",
        "turn_number": 1,
        "current_difficulty": 1,
        "previous_questions": ["What is Event Loop in JavaScript?"],
        "mode": "STUDENT",
    }
    r1 = requests.post(url, json=data1).json()
q1 = r1.get("ai_response")
print("\n=== TURN 1 RESPONSE ===")
print("AI Question:", q1)
print("Strategy:", r1.get("decision", {}).get("strategy"))
print("Next Mode:", r1.get("decision", {}).get("next_mode"))
assert r1.get("decision", {}).get("next_mode") == "STUDENT"

# Turn 2: Mechanism
data2 = {
    "topic": topic,
    "user_answer": "Synchronous code runs immediately on the call stack. Asynchronous operations like fetch or setTimeout are offloaded to Web APIs, and their callbacks are queued in the task queue or microtask queue until the call stack is empty.",
    "turn_number": 2,
    "current_difficulty": 2,
    "previous_questions": ["What is Event Loop in JavaScript?", q1],
    "mode": "STUDENT",
}
r2 = requests.post(url, json=data2).json()
q2 = r2.get("ai_response")
print("\n=== TURN 2 RESPONSE ===")
print("AI Question:", q2)
print("Strategy:", r2.get("decision", {}).get("strategy"))
print("Next Mode:", r2.get("decision", {}).get("next_mode"))
assert r2.get("decision", {}).get("next_mode") == "STUDENT"
assert q2 != q1, "Questions must not be identical!"

# Turn 3: User gets stuck -> Teacher Mode
data3 = {
    "topic": topic,
    "user_answer": "I am stuck, can you explain how microtasks are prioritized over macrotasks?",
    "turn_number": 3,
    "current_difficulty": 2,
    "previous_questions": ["What is Event Loop in JavaScript?", q1, q2],
    "mode": "STUDENT",
    "is_stuck_request": True,
    "gap": "Microtask vs Macrotask Queue Priority",
}
r3 = requests.post(url, json=data3).json()
t3 = r3.get("ai_response")
print("\n=== TURN 3 (TEACHER MODE ENTRY) ===")
print("Teacher Explanation:", t3[:200] + "...")
print("Strategy:", r3.get("decision", {}).get("strategy"))
print("Next Mode:", r3.get("decision", {}).get("next_mode"))
assert r3.get("decision", {}).get("next_mode") == "TEACHER"

# Turn 4: User gives empty readiness ("Got it, I understand now!")
data4 = {
    "topic": topic,
    "user_answer": "Got it, I understand now!",
    "turn_number": 4,
    "current_difficulty": 2,
    "previous_questions": ["What is Event Loop in JavaScript?", q1, q2],
    "mode": "TEACHER",
    "is_readiness_signal": True,
    "gap": "Microtask vs Macrotask Queue Priority",
    "interrupted_question": {"content": q2},
}
r4 = requests.post(url, json=data4).json()
v4 = r4.get("ai_response")
print("\n=== TURN 4 (READINESS -> VERIFICATION) ===")
print("Verification Question:", v4)
print("Strategy:", r4.get("decision", {}).get("strategy"))
print("Next Mode:", r4.get("decision", {}).get("next_mode"))
assert r4.get("decision", {}).get("next_mode") == "TEACHER", "Must stay in TEACHER mode until verification passes!"
assert r4.get("decision", {}).get("strategy") == "VERIFY_UNDERSTANDING"

# Turn 5: User answers verification -> Curio checks answer, switches to STUDENT, restores interrupted question!
data5 = {
    "topic": topic,
    "user_answer": "Microtasks from Promises are completely drained until the queue is empty before the event loop picks up the next macrotask from setTimeout.",
    "turn_number": 5,
    "current_difficulty": 2,
    "previous_questions": ["What is Event Loop in JavaScript?", q1, q2],
    "mode": "TEACHER",
    "is_answering_verification": True,
    "gap": "Microtask vs Macrotask Queue Priority",
    "interrupted_question": {"content": q2},
}
r5 = requests.post(url, json=data5).json()
res5 = r5.get("ai_response")
print("\n=== TURN 5 (VERIFICATION ANSWERED -> RESTORE QUESTION) ===")
print("Restoration Response:", res5)
print("Strategy:", r5.get("decision", {}).get("strategy"))
print("Next Mode:", r5.get("decision", {}).get("next_mode"))
print("Should Restore Interrupted Question:", r5.get("decision", {}).get("should_restore_interrupted_question"))
assert r5.get("decision", {}).get("next_mode") == "STUDENT"
assert r5.get("decision", {}).get("strategy") == "RESTORE_INTERRUPTED_QUESTION"
assert q2 in res5, "Interrupted question must be restored!"

print("\n ALL MULTI-TURN PEDAGOGICAL INVARIANTS PASSED PERFECTLY!")
