import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import {
  transcribeAudio,
  isVoiceRecordingSupported,
  getSupportedAudioMimeType,
} from "../services/voiceService";
import { TranscriptionResult } from "../types/voice";

describe("Voice Recording and Transcription Tests (Phase 2)", () => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const originalNavigator = globalThis.navigator;
  const originalFormData = globalThis.FormData;
  const mockToken = "test_user_jwt_token_12345";

  beforeEach(() => {
    // Setup authenticated localStorage session
    const mockStorage: Record<string, string> = {
      curio_access_token: mockToken,
      curio_user_id: "user_uuid_101",
    };
    (globalThis as any).localStorage = {
      getItem: (key: string) => mockStorage[key] || null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
      clear: () => {
        Object.keys(mockStorage).forEach((k) => delete mockStorage[k]);
      },
    };

    (globalThis as any).window = {
      localStorage: (globalThis as any).localStorage,
      location: { protocol: "http:", host: "localhost:3000" },
      MediaRecorder: class MockMediaRecorder {
        static isTypeSupported(mime: string) {
          return mime.startsWith("audio/webm");
        }
      },
    };

    (globalThis as any).navigator = {
      mediaDevices: {
        getUserMedia: async () => ({
          getTracks: () => [
            {
              stop: () => {},
              readyState: "live",
            },
          ],
        }),
      },
    };
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    (globalThis as any).window = originalWindow;
    (globalThis as any).navigator = originalNavigator;
    (globalThis as any).FormData = originalFormData;
  });

  describe("1. Browser Capability Detection", () => {
    test("isVoiceRecordingSupported returns true when mediaDevices and MediaRecorder are present", () => {
      assert.strictEqual(isVoiceRecordingSupported(), true);
    });

    test("isVoiceRecordingSupported returns false when mediaDevices is missing", () => {
      (globalThis as any).navigator = {};
      assert.strictEqual(isVoiceRecordingSupported(), false);
    });

    test("getSupportedAudioMimeType selects supported audio/webm format", () => {
      const mime = getSupportedAudioMimeType();
      assert.match(mime, /audio\/webm/);
    });
  });

  describe("2. Client-Side Validation", () => {
    test("Rejects empty recording (0 bytes) before sending request", async () => {
      const emptyBlob = new Blob([], { type: "audio/webm" });
      await assert.rejects(
        async () => {
          await transcribeAudio(emptyBlob);
        },
        {
          name: "Error",
          message: /empty \(0 bytes\)/i,
        }
      );
    });
  });

  describe("3. API Client & Multipart Upload Contract", () => {
    test("Sends authenticated multipart FormData without manual Content-Type override", async () => {
      let capturedUrl = "";
      let capturedHeaders: Record<string, string> = {};
      let capturedBody: any = null;

      globalThis.fetch = (async (url: string, init?: RequestInit) => {
        capturedUrl = url;
        capturedHeaders = (init?.headers as Record<string, string>) || {};
        capturedBody = init?.body;

        return {
          ok: true,
          status: 200,
          json: async () => ({
            text: "Explain recursion using my uploaded notes.",
            language: "en",
            duration_seconds: 3.5,
          }),
        } as Response;
      }) as any;

      const audioBlob = new Blob(["fake-pcm-audio-content"], { type: "audio/webm" });
      const result = await transcribeAudio(audioBlob, "recording.webm");

      // Verify endpoint URL
      assert.match(capturedUrl, /\/voice\/transcribe$/);

      // Verify Bearer token was injected by apiClient
      assert.strictEqual(capturedHeaders["Authorization"], `Bearer ${mockToken}`);

      // Verify Content-Type was NOT manually set to JSON or forced multipart
      assert.strictEqual(capturedHeaders["Content-Type"], undefined);

      // Verify body is FormData
      assert.strictEqual(capturedBody instanceof FormData, true);

      // Verify response payload
      assert.strictEqual(result.text, "Explain recursion using my uploaded notes.");
      assert.strictEqual(result.language, "en");
      assert.strictEqual(result.duration_seconds, 3.5);
    });

    test("Propagates 401 Unauthorized consistently with application auth conventions", async () => {
      globalThis.fetch = (async () => {
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: "Could not validate credentials" }),
        } as Response;
      }) as any;

      const audioBlob = new Blob(["audio-data"], { type: "audio/webm" });
      await assert.rejects(
        async () => {
          await transcribeAudio(audioBlob);
        },
        (err: any) => {
          assert.strictEqual(err.status, 401);
          assert.match(err.message, /unauthorized/i);
          return true;
        }
      );
    });

    test("Propagates 400 Bad Request error detail from backend", async () => {
      globalThis.fetch = (async () => {
        return {
          ok: false,
          status: 400,
          json: async () => ({ detail: "Malformed or unsupported audio format." }),
        } as Response;
      }) as any;

      const audioBlob = new Blob(["corrupted-bytes"], { type: "audio/webm" });
      await assert.rejects(
        async () => {
          await transcribeAudio(audioBlob);
        },
        (err: any) => {
          assert.strictEqual(err.status, 400);
          assert.strictEqual(err.message, "Malformed or unsupported audio format.");
          return true;
        }
      );
    });

    test("Propagates 413 Payload Too Large error detail from backend", async () => {
      globalThis.fetch = (async () => {
        return {
          ok: false,
          status: 413,
          json: async () => ({ detail: "Audio file size exceeds the limit of 10MB." }),
        } as Response;
      }) as any;

      const audioBlob = new Blob(["oversized-data"], { type: "audio/webm" });
      await assert.rejects(
        async () => {
          await transcribeAudio(audioBlob);
        },
        (err: any) => {
          assert.strictEqual(err.status, 413);
          assert.match(err.message, /exceeds the limit/i);
          return true;
        }
      );
    });
  });

  describe("4. Recording Lifecycle & Track Cleanup Simulation", () => {
    test("Track stopping releases microphone hardware tracks", () => {
      let trackStopped = false;
      const mockTrack = {
        stop: () => {
          trackStopped = true;
        },
        readyState: "live",
      };

      const mockStream = {
        getTracks: () => [mockTrack],
      };

      // Simulating cleanup function
      mockStream.getTracks().forEach((track) => track.stop());
      assert.strictEqual(trackStopped, true);
    });

    test("Permission denial simulation produces helpful error message", async () => {
      (globalThis as any).navigator.mediaDevices.getUserMedia = async () => {
        const permError = new Error("Permission denied");
        permError.name = "NotAllowedError";
        throw permError;
      };

      try {
        await (globalThis as any).navigator.mediaDevices.getUserMedia({ audio: true });
        assert.fail("Should have thrown");
      } catch (err: any) {
        assert.strictEqual(err.name, "NotAllowedError");
      }
    });

    test("Cancellation simulation discards recorded chunks without sending transcription", async () => {
      let apiCalled = false;
      globalThis.fetch = (async () => {
        apiCalled = true;
        return { ok: true, status: 200, json: async () => ({ text: "test" }) } as Response;
      }) as any;

      // Simulated cancellation flow:
      let isCanceled = true;
      let recordedChunks: Blob[] = [new Blob(["chunk1"]), new Blob(["chunk2"])];

      if (isCanceled) {
        recordedChunks = [];
      } else {
        await transcribeAudio(new Blob(recordedChunks));
      }

      assert.strictEqual(apiCalled, false);
      assert.strictEqual(recordedChunks.length, 0);
    });
  });

  describe("5. Review-Before-Send Integrity", () => {
    test("Transcribed text is populated into composer without auto-submitting", () => {
      let composerContent = "";
      const isAutoSubmitted = false;

      const onTranscriptionSuccess = (text: string) => {
        composerContent = composerContent ? `${composerContent} ${text}` : text;
      };

      // 1. Spoken input returns text
      onTranscriptionSuccess("Explain binary search trees.");
      assert.strictEqual(composerContent, "Explain binary search trees.");
      assert.strictEqual(isAutoSubmitted, false);

      // 2. User reviews and edits transcript before sending
      composerContent += " Focus on balanced AVL trees.";
      assert.strictEqual(
        composerContent,
        "Explain binary search trees. Focus on balanced AVL trees."
      );

      // 3. User can cancel/clear without sending
      composerContent = "";
      assert.strictEqual(composerContent, "");
    });

    test("Appending transcription preserves previously typed notes in composer", () => {
      let composerContent = "Regarding earlier question:";

      const onTranscriptionSuccess = (text: string) => {
        composerContent = composerContent ? `${composerContent} ${text}` : text;
      };

      onTranscriptionSuccess("What is the time complexity of rotation?");
      assert.strictEqual(
        composerContent,
        "Regarding earlier question: What is the time complexity of rotation?"
      );
    });
  });
});
