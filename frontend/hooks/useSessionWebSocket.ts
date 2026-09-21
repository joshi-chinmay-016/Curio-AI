"use client";

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/stores/sessionStore";
import { ChatMessage, SessionWebSocketMessage } from "@/types/session";
import { curioToast } from "@/components/curio/CurioToast";

export function useSessionWebSocket(sessionId: string) {
  const router = useRouter();
  const wsRef = useRef<WebSocket | null>(null);
  const isMockRef = useRef<boolean>(true);

  const {
    topicName,
    mode,
    setMode,
    addMessage,
    setThinking,
    setConfidence,
    setTurnNumber,
    currentTurnNumber,
    confidence,
    setActiveGap,
    setInterruptedQuestion,
    interruptedQuestion,
    messages,
  } = useSessionStore();

  const handleIncomingMessage = useCallback(
    (msg: SessionWebSocketMessage) => {
      setThinking(false);

      if (msg.confidence !== undefined) {
        setConfidence(msg.confidence);
      }
      if (msg.turnNumber !== undefined) {
        setTurnNumber(msg.turnNumber);
      }

      switch (msg.type) {
        case "mode_change":
          if (msg.mode === "TEACHER") setMode("TEACHER");
          else if (msg.mode === "STUDENT") setMode("STUDENT");
          break;

        case "gap_detected":
          if (msg.gap) {
            setActiveGap(msg.gap);
            curioToast.error(
              "GAP IDENTIFIED",
              `${msg.gap.title} flagged for review.`
            );
          }
          break;

        case "teacher_start": {
          const currentTopic = topicName || "the concept";
          const gap = msg.gap || {
            conceptId: `${currentTopic.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-core-invariants`,
            title: `${currentTopic}: Core Mechanism & Boundary Conditions`,
            severity: "HIGH" as const,
          };
          setActiveGap(gap);

          // Save last curio question as interrupted question if not set
          const lastCurioMsg = [...messages]
            .reverse()
            .find((m) => m.role === "curio" && m.type === "question");
          if (lastCurioMsg) {
            setInterruptedQuestion(lastCurioMsg);
          }

          setMode("TEACHER");

          // Add separator and teacher message
          addMessage({
            id: "sep_" + Date.now(),
            role: "system",
            type: "separator",
            content: "── TEACHER MODE ACTIVATED ──",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            mode: "TEACHER",
          });

          addMessage({
            id: "msg_teach_" + Date.now(),
            role: "curio",
            type: "teacher_content",
            content:
              msg.content ||
              `Let's isolate this specific part of **${currentTopic}** before continuing.\n\nWhat is the fundamental requirement or invariant that must hold true at every stage of **${currentTopic}**, and what happens if that invariant is violated?`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            turnNumber: currentTurnNumber + 1,
            mode: "TEACHER",
            gapReference: gap.conceptId,
          });
          break;
        }

        case "teacher_end": {
          // Verification passed
          curioToast.success("CONCEPT VERIFIED", "Returning to student inquiry mode.");

          addMessage({
            id: "sep_ret_" + Date.now(),
            role: "system",
            type: "separator",
            content: "── RETURNING TO STUDENT MODE ──",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            mode: "STUDENT",
          });

          // Re-introduce interrupted question with restored highlight
          if (interruptedQuestion) {
            addMessage({
              id: "msg_restored_" + Date.now(),
              role: "curio",
              type: "question",
              content: interruptedQuestion.content,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              turnNumber: currentTurnNumber + 1,
              mode: "STUDENT",
              isRestored: true,
            });
            setInterruptedQuestion(undefined);
          }

          setActiveGap(undefined);
          setMode("STUDENT");
          break;
        }

        case "session_complete":
          router.push(`/session/${sessionId}/report`);
          break;

        case "question":
        default:
          addMessage({
            id: "msg_curio_" + Date.now(),
            role: "curio",
            type: "question",
            content: msg.content,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            turnNumber: (msg.turnNumber || currentTurnNumber) + 1,
            mode: msg.mode === "TEACHER" ? "TEACHER" : "STUDENT",
          });
          break;
      }
    },
    [
      addMessage,
      currentTurnNumber,
      interruptedQuestion,
      messages,
      router,
      setActiveGap,
      setConfidence,
      setInterruptedQuestion,
      setMode,
      setThinking,
      setTurnNumber,
      sessionId,
      topicName,
    ]
  );

  // Send message
  // Send message
  const sendMessage = useCallback(
    async (content: string) => {
      const cleanContent = content.trim();
      if (!cleanContent) return;

      const userMsg: ChatMessage = {
        id: "msg_learner_" + Date.now(),
        role: "learner",
        type: "answer",
        content: cleanContent,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        turnNumber: currentTurnNumber + 1,
        mode: mode,
      };

      addMessage(userMsg);
      setTurnNumber(currentTurnNumber + 1);
      setThinking(true);

      // If connected to real WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "answer", content: cleanContent }));
        return;
      }

      // Offline / Local Development Fallback using SessionRepository
      try {
        const { getSessionRepository } = await import("@/services/sessionRepository");
        const repo = getSessionRepository();

        // Brief realistic thinking delay for natural conversation feel
        await new Promise((resolve) => setTimeout(resolve, 800));

        const turnResult = await repo.sendMessage(sessionId, cleanContent);
        setThinking(false);

        if (turnResult.evaluation) {
          setConfidence(Math.round(turnResult.decision.confidence));
        }

        const nextMode = turnResult.decision.next_mode;

        // Transition: STUDENT -> TEACHER
        if (nextMode === "TEACHER" && mode !== "TEACHER") {
          const gap = {
            conceptId: turnResult.decision.active_concept,
            title: turnResult.decision.active_concept,
            severity: "HIGH" as const,
          };
          setActiveGap(gap);

          // Snapshot last student question if not already snapshotted
          const lastQuestion = [...messages]
            .reverse()
            .find((m) => m.role === "curio" && m.type === "question");
          if (lastQuestion) {
            setInterruptedQuestion(lastQuestion);
          }

          setMode("TEACHER");

          // Subtle transition separator
          addMessage({
            id: "sep_" + Date.now(),
            role: "system",
            type: "separator",
            content: "── LET'S PAUSE THE QUESTIONS FOR A MOMENT ──",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            mode: "TEACHER",
          });

          // Teacher message
          addMessage({
            id: turnResult.ai_message.message_id,
            role: "curio",
            type: "teacher_content",
            content: turnResult.ai_message.content,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            turnNumber: currentTurnNumber + 2,
            mode: "TEACHER",
            gapReference: gap.conceptId,
          });

          curioToast.error(
            "CONCEPT GAP DETECTED",
            `Curio switched to Teacher Mode to clarify: ${gap.title}`
          );
          return;
        }

        // Transition: TEACHER -> STUDENT (Verification Passed or max attempts reached)
        if (turnResult.decision.should_restore_interrupted_question) {
          setMode("STUDENT");
          setActiveGap(undefined);

          const isLimitFallback = turnResult.decision.reason?.includes("Maximum Teacher attempts") || false;
          const isVerified = !isLimitFallback && (turnResult.evaluation?.correctness || 0) >= 0.7 && (turnResult.evaluation?.misconceptions?.length || 0) === 0;

          // Subtle transition separator
          addMessage({
            id: "sep_ret_" + Date.now(),
            role: "system",
            type: "separator",
            content: isVerified
              ? "── CONCEPT VERIFIED · RETURNING TO INQUIRY ──"
              : "── RETURNING TO FOUNDATIONAL INQUIRY ──",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            mode: "STUDENT",
          });

          // Restored question
          addMessage({
            id: turnResult.ai_message.message_id,
            role: "curio",
            type: "question",
            content: turnResult.ai_message.content,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            turnNumber: currentTurnNumber + 2,
            mode: "STUDENT",
            isRestored: true,
          });

          setInterruptedQuestion(undefined);
          if (isVerified) {
            curioToast.success("CONCEPT VERIFIED", "Interrupted question restored. Returning to inquiry.");
          } else {
            curioToast.info("RETURNING TO INQUIRY", "Resuming exploration at a foundational level.");
          }
          return;
        }

        // Continuing Teacher Mode
        if (nextMode === "TEACHER") {
          addMessage({
            id: turnResult.ai_message.message_id,
            role: "curio",
            type: "teacher_content",
            content: turnResult.ai_message.content,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            turnNumber: currentTurnNumber + 2,
            mode: "TEACHER",
          });
          return;
        }

        // Normal Student Mode Question
        addMessage({
          id: turnResult.ai_message.message_id,
          role: "curio",
          type: "question",
          content: turnResult.ai_message.content,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          turnNumber: currentTurnNumber + 2,
          mode: "STUDENT",
        });
      } catch (err) {
        console.error("Failed to process message:", err);
        setThinking(false);
      }
    },
    [
      addMessage,
      currentTurnNumber,
      messages,
      mode,
      sessionId,
      setActiveGap,
      setConfidence,
      setInterruptedQuestion,
      setMode,
      setThinking,
      setTurnNumber,
    ]
  );

  // Trigger I'm Stuck (Explicit learner override to enter Teacher Mode)
  const triggerStuck = useCallback(() => {
    sendMessage("I'm stuck, can you explain this?");
  }, [sendMessage]);

  // Trigger End Session
  const triggerEndSession = useCallback(async () => {
    setMode("EVALUATING");
    try {
      const { getSessionRepository } = await import("@/services/sessionRepository");
      const repo = getSessionRepository();
      await repo.endSession(sessionId);
    } catch (err) {
      console.warn("End session fallback:", err);
    }
    setTimeout(() => {
      router.push(`/session/${sessionId}/report`);
    }, 2000);
  }, [router, sessionId, setMode]);

  // Attempt real WebSocket connection
  useEffect(() => {
    if (!sessionId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = process.env.NEXT_PUBLIC_WS_HOST || "localhost:8000";
    const wsUrl = `${protocol}//${host}/api/v1/sessions/${sessionId}/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        isMockRef.current = false;
        console.log(`[WebSocket] Connected to ${wsUrl}`);
      };

      ws.onmessage = (event) => {
        try {
          const data: SessionWebSocketMessage = JSON.parse(event.data);
          handleIncomingMessage(data);
        } catch (e) {
          console.error("Failed to parse incoming WS message:", e);
        }
      };

      ws.onerror = () => {
        isMockRef.current = true;
      };

      ws.onclose = () => {
        isMockRef.current = true;
      };

      return () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };
    } catch {
      isMockRef.current = true;
    }
  }, [sessionId, handleIncomingMessage]);

  return {
    sendMessage,
    triggerStuck,
    triggerEndSession,
  };
}
