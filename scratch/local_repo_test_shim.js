const fs = require("fs");
const path = require("path");

// Read and strip TS annotations or compile
const tsContent = fs.readFileSync(
  path.resolve(__dirname, "../frontend/services/sessionRepository/LocalSessionRepository.ts"),
  "utf8"
);

// Minimal transpiler for typescript to run in Node
const ts = require("../frontend/node_modules/typescript");
const jsContent = ts.transpileModule(tsContent, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;

const m = { exports: {} };
const fn = new Function("module", "exports", "require", jsContent);
fn(m, m.exports, require);

module.exports = m.exports;
