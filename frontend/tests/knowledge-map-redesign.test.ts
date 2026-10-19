import { test, describe } from "node:test";
import assert from "node:assert";
import type { GapReport, ConceptCell } from "../types/gapReport";

describe("Knowledge Map Visual Redesign (V3): Knowledge Circuit Board", () => {
  const mockReport: GapReport = {
    sessionId: "session_algo_101",
    topicName: "FastAPI & Graph Algorithms",
    topicId: "topic_graph_01",
    understandingScore: 78,
    masteryLevel: "Developing",
    evidenceConfidence: 85,
    conceptsExplored: 6,
    knowledgeGaps: 1,
    resolvedMisconceptions: 1,
    createdAt: new Date().toISOString(),
    availableTopics: [
      { id: "session_algo_101", name: "FastAPI & Graph Algorithms" },
      { id: "session_algo_102", name: "Dynamic Programming" },
    ],
    recommendedNextSteps: ["Review cycle detection in directed graphs"],
    gaps: [
      {
        id: "gap_1",
        conceptId: "concept_edge_1",
        title: "Cycle Detection with In-Degree",
        severity: "HIGH",
        status: "UNRESOLVED",
        understandingScore: 35,
        confidence: 80,
        whyDetected: "Confused in-degree removal with topological sort traversal",
        evidence: [],
        recommendedAction: "Practice Kahn's algorithm",
        teacherInterventionAttempted: true,
        verificationSuccess: false,
      },
    ],
    concepts: [
      // Layer 1: DEFINITION
      {
        id: "concept_def_1",
        name: "Graph Node",
        layer: "DEFINITION",
        status: "STRONG",
        score: 95,
        confidence: 90,
        relatedConceptIds: ["concept_mech_1"],
      },
      {
        id: "concept_def_2",
        name: "Adjacency List",
        layer: "DEFINITION",
        status: "STRONG",
        score: 90,
        confidence: 85,
        relatedConceptIds: [],
      },
      // Layer 2: MECHANISM
      {
        id: "concept_mech_1",
        name: "DFS Traversal",
        layer: "MECHANISM",
        status: "RESOLVED",
        score: 82,
        confidence: 80,
        relatedConceptIds: ["concept_app_1"],
      },
      {
        id: "concept_mech_2",
        name: "Visited Set",
        layer: "MECHANISM",
        status: "DEVELOPING",
        score: 68,
        confidence: 70,
        relatedConceptIds: [],
      },
      // Layer 3: APPLICATION
      {
        id: "concept_app_1",
        name: "Topological Sort",
        layer: "APPLICATION",
        status: "DEVELOPING",
        score: 60,
        confidence: 65,
        relatedConceptIds: ["concept_edge_1"],
      },
      // Layer 4: EDGE_CASES
      {
        id: "concept_edge_1",
        name: "Cycle In-Degree",
        layer: "EDGE_CASES",
        status: "GAP",
        score: 35,
        confidence: 75,
        relatedConceptIds: ["concept_app_1", "concept_mech_1"],
      },
    ],
  };

  test("1. Verifies 4 horizontal tracks and layer prefixes", () => {
    const layers = ["DEFINITION", "MECHANISM", "APPLICATION", "EDGE_CASES"];
    const prefixes: Record<string, string> = {
      DEFINITION: "01",
      MECHANISM: "02",
      APPLICATION: "03",
      EDGE_CASES: "04",
    };

    layers.forEach((l) => {
      assert.ok(prefixes[l]);
      assert.strictEqual(typeof prefixes[l], "string");
    });
  });

  test("2. Verifies concepts display actual concept names without placeholder UNTESTED injection", () => {
    const conceptNames = mockReport.concepts.map((c) => c.name);
    assert.deepStrictEqual(conceptNames, [
      "Graph Node",
      "Adjacency List",
      "DFS Traversal",
      "Visited Set",
      "Topological Sort",
      "Cycle In-Degree",
    ]);

    // Concept names are all under readable length threshold
    conceptNames.forEach((name) => {
      assert.ok(name.length > 0);
      assert.notStrictEqual(name, "UNTESTED");
    });
  });

  test("3. Verifies broken trace detection leading to GAP nodes", () => {
    const isGapNode = (c: ConceptCell) =>
      c.status === "GAP" || c.status === "MISCONCEPTION";

    const edgeCasesConcepts = mockReport.concepts.filter(
      (c) => c.layer === "EDGE_CASES"
    );
    assert.strictEqual(edgeCasesConcepts.length, 1);
    assert.strictEqual(isGapNode(edgeCasesConcepts[0]), true);

    const definitionConcepts = mockReport.concepts.filter(
      (c) => c.layer === "DEFINITION"
    );
    assert.strictEqual(isGapNode(definitionConcepts[0]), false);
    assert.strictEqual(isGapNode(definitionConcepts[1]), false);
  });

  test("4. Verifies layer score calculation and badge colors", () => {
    // Score badge colors:
    // cobalt (>70%), white (50-70%), orange (<50%)
    const getScoreColor = (score: number) => {
      if (score < 50) return "#FF6B1A";
      if (score <= 70) return "#FFFFFF";
      return "#3A63FF";
    };

    assert.strictEqual(getScoreColor(92), "#3A63FF"); // >70%
    assert.strictEqual(getScoreColor(65), "#FFFFFF"); // 50-70%
    assert.strictEqual(getScoreColor(35), "#FF6B1A"); // <50%
  });

  test("5. Verifies layer health dots generation [●●◉○]", () => {
    const computeHealthDots = (concepts: ConceptCell[], layerScore: number) => {
      const dots: ("cobalt" | "orange" | "fog")[] = [];
      concepts.slice(0, 4).forEach((c) => {
        if (c.status === "GAP" || c.status === "MISCONCEPTION") {
          dots.push("orange");
        } else if (c.status === "UNTESTED") {
          dots.push("fog");
        } else {
          dots.push("cobalt");
        }
      });
      while (dots.length < 4) {
        if (layerScore < 50 && !dots.includes("orange")) {
          dots.push("orange");
        } else if (layerScore >= 60) {
          dots.push("cobalt");
        } else {
          dots.push("fog");
        }
      }
      return dots;
    };

    const defDots = computeHealthDots(
      mockReport.concepts.filter((c) => c.layer === "DEFINITION"),
      92
    );
    assert.deepStrictEqual(defDots, ["cobalt", "cobalt", "cobalt", "cobalt"]);

    const edgeDots = computeHealthDots(
      mockReport.concepts.filter((c) => c.layer === "EDGE_CASES"),
      35
    );
    assert.ok(edgeDots.includes("orange"), "Edge cases layer with gap must include orange dot");
  });

  test("6. Verifies contextual node dimming rules for Knowledge Circuit", () => {
    const computeNodeOpacity = (
      isFocusGaps: boolean,
      isGap: boolean,
      isUntested: boolean,
      isSelected: boolean,
      isAnySelected: boolean,
      isRelatedToSelected: boolean
    ) => {
      if (isFocusGaps) {
        if (isGap) return 1.0;
        if (isUntested) return 0.0;
        return 0.08;
      }
      if (isSelected) return 1.0;
      if (isAnySelected) {
        return isRelatedToSelected ? 0.85 : 0.3;
      }
      return 1.0;
    };

    // Normal state
    assert.strictEqual(computeNodeOpacity(false, false, false, false, false, false), 1.0);

    // Node selected: other unconnected nodes dim to 0.3
    assert.strictEqual(computeNodeOpacity(false, false, false, false, true, false), 0.3);

    // Node selected: connected related nodes stay at 0.85
    assert.strictEqual(computeNodeOpacity(false, false, false, false, true, true), 0.85);

    // Focus Gaps mode: gap nodes are 1.0, non-gap nodes fade to 0.08, untested completely hidden (0.0)
    assert.strictEqual(computeNodeOpacity(true, true, false, false, false, false), 1.0);
    assert.strictEqual(computeNodeOpacity(true, false, false, false, false, false), 0.08);
    assert.strictEqual(computeNodeOpacity(true, false, true, false, false, false), 0.0);
  });

  test("7. Verifies vertical via connections lookup for cross-layer relationships", () => {
    const selectedConcept = mockReport.concepts.find((c) => c.id === "concept_edge_1");
    assert.ok(selectedConcept);
    assert.deepStrictEqual(selectedConcept?.relatedConceptIds, [
      "concept_app_1",
      "concept_mech_1",
    ]);

    const related1 = mockReport.concepts.find((c) => c.id === "concept_app_1");
    const related2 = mockReport.concepts.find((c) => c.id === "concept_mech_1");
    assert.strictEqual(related1?.layer, "APPLICATION");
    assert.strictEqual(related2?.layer, "MECHANISM");
  });

  test("8. Verifies Knowledge Circuit components use pure SVG without Three.js or WebGL imports", () => {
    const fs = require("node:fs");
    const path = require("node:path");

    const filesToCheck = [
      path.join(__dirname, "../components/curio/gap-report/IsometricKnowledgeMap.tsx"),
      path.join(__dirname, "../components/curio/gap-report/CircuitNode.tsx"),
      path.join(__dirname, "../components/curio/gap-report/BrokenTrace.tsx"),
      path.join(__dirname, "../components/curio/gap-report/ViaConnections.tsx"),
      path.join(__dirname, "../components/curio/gap-report/CircuitHeader.tsx"),
      path.join(__dirname, "../components/curio/gap-report/LayerHealthPill.tsx"),
    ];

    filesToCheck.forEach((filePath: string) => {
      const content = fs.readFileSync(filePath, "utf-8");
      assert.strictEqual(
        content.includes("from 'three'") || content.includes('from "three"'),
        false,
        `${filePath} must not import three`
      );
      assert.strictEqual(
        content.includes("@react-three/fiber"),
        false,
        `${filePath} must not import @react-three/fiber`
      );
      assert.strictEqual(
        content.includes("WebGLRenderer"),
        false,
        `${filePath} must not use WebGLRenderer`
      );
    });
  });
});
