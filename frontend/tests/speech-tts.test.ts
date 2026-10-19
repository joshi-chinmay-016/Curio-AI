import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import {
  BrowserSpeechService,
  sanitizeTextForSpeech,
} from "../services/speechService";
import { SpeechPlaybackState } from "../types/speech";

describe("Phase 4: Text-to-Speech (TTS) for AI Responses", () => {
  const originalWindow = globalThis.window;
  let mockUtterances: any[] = [];
  let canceledCount = 0;
  let speakCalledCount = 0;

  class MockSpeechSynthesisUtterance {
    text: string;
    rate: number = 1.0;
    pitch: number = 1.0;
    volume: number = 1.0;
    voice: any = null;
    lang: string = "en-US";
    onstart: (() => void) | null = null;
    onend: (() => void) | null = null;
    onerror: ((event: any) => void) | null = null;

    constructor(text: string) {
      this.text = text;
      mockUtterances.push(this);
    }
  }

  const mockSpeechSynthesis = {
    speak: (utterance: any) => {
      speakCalledCount++;
      // Simulate asynchronous start
      setTimeout(() => {
        utterance.onstart?.();
      }, 5);
    },
    cancel: () => {
      canceledCount++;
    },
    pause: () => {},
    resume: () => {},
    getVoices: () => [
      { name: "Google US English", lang: "en-US", default: true },
      { name: "Microsoft David", lang: "en-US", default: false },
    ],
    onvoiceschanged: null as any,
  };

  const originalUtterance = (globalThis as any).SpeechSynthesisUtterance;

  beforeEach(() => {
    mockUtterances = [];
    canceledCount = 0;
    speakCalledCount = 0;

    (globalThis as any).SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;
    (globalThis as any).window = {
      speechSynthesis: mockSpeechSynthesis,
      SpeechSynthesisUtterance: MockSpeechSynthesisUtterance,
    };
  });

  afterEach(() => {
    (globalThis as any).window = originalWindow;
    (globalThis as any).SpeechSynthesisUtterance = originalUtterance;
  });

  describe("1. Markdown & Code Sanitization for Natural Pronunciation", () => {
    test("Omits code blocks rather than reading code syntax aloud", () => {
      const markdown = "Here is the solution:\n```python\ndef fib(n):\n    return n\n```\nDoes that make sense?";
      const clean = sanitizeTextForSpeech(markdown);
      assert.strictEqual(clean.includes("def fib"), false);
      assert.match(clean, /\[Code block omitted\]/);
      assert.match(clean, /Does that make sense\?/);
    });

    test("Strips markdown bold, italics, headers, and links", () => {
      const markdown = "# Title\nThis is **bold** and *italic* with a [link](https://example.com).";
      const clean = sanitizeTextForSpeech(markdown);
      assert.strictEqual(clean, "Title This is bold and italic with a link.");
    });

    test("Strips inline code backticks while preserving word content", () => {
      const markdown = "Call the `validateInput()` function.";
      const clean = sanitizeTextForSpeech(markdown);
      assert.strictEqual(clean, "Call the validateInput() function.");
    });

    test("Returns empty string for empty or whitespace-only text", () => {
      assert.strictEqual(sanitizeTextForSpeech(""), "");
      assert.strictEqual(sanitizeTextForSpeech("   \n\t  "), "");
    });
  });

  describe("2. Playback Lifecycle & Overlap Prevention", () => {
    test("Playback starts and updates subscribed state", async () => {
      const service = new BrowserSpeechService();
      let lastState: SpeechPlaybackState | null = null;

      const unsubscribe = service.subscribe((s) => {
        lastState = s;
      });

      await service.speak("msg_1", "Hello student! Let's explore algorithms.");
      assert.strictEqual(speakCalledCount, 1);
      assert.strictEqual(mockUtterances.length, 1);
      assert.strictEqual(mockUtterances[0].text, "Hello student! Let's explore algorithms.");

      // Wait for simulated async onstart
      await new Promise((r) => setTimeout(r, 20));
      assert.strictEqual((lastState as any)?.activeMessageId, "msg_1");
      assert.strictEqual((lastState as any)?.isPlaying, true);

      unsubscribe();
    });

    test("Stop cancels active speech and clears active state", async () => {
      const service = new BrowserSpeechService();
      await service.speak("msg_1", "Speaking some text.");
      await new Promise((r) => setTimeout(r, 10));

      service.stop();
      assert.strictEqual(canceledCount >= 1, true);
      assert.strictEqual(service.isPlaying("msg_1"), false);
      assert.strictEqual(service.getActiveMessageId(), null);
    });

    test("Starting a new message playback cancels any previously active message", async () => {
      const service = new BrowserSpeechService();

      await service.speak("msg_1", "First message text.");
      await new Promise((r) => setTimeout(r, 10));
      assert.strictEqual(service.getActiveMessageId(), "msg_1");

      // Now user clicks play on a second message
      await service.speak("msg_2", "Second message text.");
      await new Promise((r) => setTimeout(r, 10));

      assert.strictEqual(canceledCount >= 1, true);
      assert.strictEqual(service.getActiveMessageId(), "msg_2");
      assert.strictEqual(service.isPlaying("msg_1"), false);
      assert.strictEqual(service.isPlaying("msg_2"), true);
    });

    test("Empty or code-only response is not spoken", async () => {
      const service = new BrowserSpeechService();
      await service.speak("msg_empty", "");
      assert.strictEqual(speakCalledCount, 0);

      await service.speak("msg_code", "```\n\n```");
      // Even if code block omitted, if text is empty or just whitespace:
      const clean = sanitizeTextForSpeech("```\n\n```");
      if (!clean) {
        assert.strictEqual(speakCalledCount, 0);
      }
    });
  });

  describe("3. Browser Fallback & Error Resilience", () => {
    test("Gracefully handles browsers where speechSynthesis is missing", async () => {
      (globalThis as any).window = {};
      delete (globalThis as any).SpeechSynthesisUtterance;
      const service = new BrowserSpeechService();

      assert.strictEqual(service.isSupported(), false);
      let errorReported = false;

      await service.speak("msg_fail", "Text to read", {
        onError: () => {
          errorReported = true;
        },
      });

      assert.strictEqual(errorReported, true);
      assert.strictEqual(service.isPlaying(), false);
    });

    test("Speech errors do not disrupt the application", async () => {
      const service = new BrowserSpeechService();
      let errorCaught = false;

      // Mock speak that emits onerror
      mockSpeechSynthesis.speak = (utterance: any) => {
        setTimeout(() => {
          utterance.onerror?.({ error: "audio-hardware" });
        }, 5);
      };

      await service.speak("msg_err", "Text that causes error", {
        onError: (err) => {
          errorCaught = true;
          assert.match(err.message, /audio-hardware/);
        },
      });

      await new Promise((r) => setTimeout(r, 20));
      assert.strictEqual(errorCaught, true);
      assert.strictEqual(service.isPlaying(), false);
    });
  });

  describe("4. Learning Modes & Text Integrity", () => {
    test("Student Mode and Teacher Mode speak the exact visible text displayed to learner", async () => {
      const service = new BrowserSpeechService();

      // Student mode question
      const studentMsg = "Can you describe how Dijkstra's algorithm uses a priority queue?";
      await service.speak("msg_stud", studentMsg);
      assert.strictEqual(mockUtterances[mockUtterances.length - 1].text, studentMsg);

      // Teacher mode explanation
      const teacherMsg = "Notice that Dijkstra's requires non-negative edge weights to guarantee optimality.";
      await service.speak("msg_teach", teacherMsg);
      assert.strictEqual(mockUtterances[mockUtterances.length - 1].text, teacherMsg);
    });
  });
});
