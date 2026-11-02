import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { KnowledgeGraphSchema, contentHash } from './understand-anything/understand-anything-plugin/packages/core/dist/index.js';

const workspace = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const project = path.resolve(workspace, process.argv[2] || '.');
const dataDir = path.join(project, fs.existsSync(path.join(project, '.understand-anything')) ? '.understand-anything' : '.ua');
const read = (name) => JSON.parse(fs.readFileSync(path.join(dataDir, name), 'utf8'));
const graph = KnowledgeGraphSchema.parse(read('knowledge-graph.json'));
const scan = read('intermediate/scan-result.json');
const ids = new Set(graph.nodes.map((node) => node.id));
assert.equal(ids.size, graph.nodes.length, 'Duplicate node IDs');
const inventory = new Set(scan.files.map((file) => file.path));
const represented = new Set();
const currentHashes = new Map();
for (const node of graph.nodes) {
    if (!node.filePath) continue;
    assert(inventory.has(node.filePath), `File outside scan inventory: ${node.filePath}`);
    assert(!/(^|\/)(\.env(?:\.|$)|node_modules|\.aws|\.secrets|\.ua|\.understand-anything)(\/|$)/.test(node.filePath), `Private/runtime path: ${node.filePath}`);
    const absolute = path.resolve(project, node.filePath);
    const relative = path.relative(project, absolute);
    assert(relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative), 'Path escapes project');
    const source = fs.readFileSync(absolute, 'utf8');
    currentHashes.set(node.filePath, contentHash(source));
    represented.add(node.filePath);
    if (node.lineRange) {
        const [start, end] = node.lineRange;
        assert(Number.isInteger(start) && Number.isInteger(end) && start >= 1 && end >= start && end <= source.split('\n').length, `Invalid source range: ${node.id}`);
    }
}
for (const file of inventory) assert(represented.has(file), `Missing analyzed file: ${file}`);
const fingerprintsPath = path.join(dataDir, 'fingerprints.json');
if (fs.existsSync(fingerprintsPath)) {
    const fingerprints = JSON.parse(fs.readFileSync(fingerprintsPath, 'utf8'));
    for (const file of inventory) {
        assert.equal(fingerprints.files[file]?.contentHash, currentHashes.get(file), `Source changed since analysis: ${file}`);
    }
}
const linked = new Set();
for (const edge of graph.edges) {
    assert(ids.has(edge.source) && ids.has(edge.target), `Dangling edge: ${edge.source} -> ${edge.target}`);
    linked.add(`${edge.source}|${edge.target}|${edge.type}`);
}
const fileNodes = graph.nodes.filter((node) => node.filePath && !['function', 'class', 'concept', 'module'].includes(node.type));
const nodesForFile = new Map();
for (const node of fileNodes) {
    const candidates = nodesForFile.get(node.filePath) || [];
    candidates.push(node.id);
    nodesForFile.set(node.filePath, candidates);
}
for (const [source, targets] of Object.entries(scan.importMap)) {
    for (const target of targets) {
        assert((nodesForFile.get(source) || []).some((from) =>
            (nodesForFile.get(target) || []).some((to) => linked.has(`${from}|${to}|imports`))),
        `Missing deterministic import: ${source} -> ${target}`);
    }
}
const assignments = new Set();
for (const layer of graph.layers) {
    for (const id of layer.nodeIds) {
        assert(ids.has(id), `Unknown layer member: ${id}`);
        assert(!assignments.has(id), `Node assigned to multiple layers: ${id}`);
        assignments.add(id);
    }
}
for (const node of fileNodes) assert(assignments.has(node.id), `File node without layer: ${node.id}`);
assert(graph.tour.length > 0, 'Missing learning tour');
for (const step of graph.tour) for (const id of step.nodeIds) assert(ids.has(id), `Unknown tour node: ${id}`);
const scopePath = path.join(dataDir, 'scope-report.json');
if (fs.existsSync(scopePath)) {
    const scope = JSON.parse(fs.readFileSync(scopePath, 'utf8'));
    assert.equal(scope.analyzedFiles, inventory.size, 'Scope report disagrees with scanned inventory');
    for (const directory of scope.directories) {
        assert(ids.has(`module:${directory.directory}`), `Directory missing from workspace graph: ${directory.directory}`);
    }
}
console.log(`PASS: ${inventory.size} files, ${graph.nodes.length} nodes, ${graph.edges.length} edges, ${graph.layers.length} layers, ${graph.tour.length} tour steps.`);
