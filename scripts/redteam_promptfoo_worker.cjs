// JSON stdin/stdout bridge to promptfoo's public redteam API. No inference calls.
const fs = require('node:fs');
const path = require('node:path');
process.env.PROMPTFOO_DISABLE_TELEMETRY = '1';
process.env.PROMPTFOO_DISABLE_REMOTE_GENERATION = 'true';
process.env.LOG_LEVEL = 'error';
const root = path.resolve(__dirname, '..');
const { redteam } = require(path.join(root, '.runtime/redtools-node/node_modules/promptfoo'));
const version = require(path.join(root, '.runtime/redtools-node/node_modules/promptfoo/package.json')).version;
const localIds = ['base64', 'hex', 'rot13', 'leetspeak', 'homoglyph', 'morse',
  'piglatin', 'camelcase', 'emoji', 'arabic-presentation-forms', 'jailbreak-templates'];
async function transform(id, text) {
  if (!localIds.includes(id)) throw new Error('Strategy is not a supported local transformation');
  // Stable results allow the application to replay a recorded agent conversation.
  let seed = 2166136261;
  for (const c of id + text) seed = Math.imul(seed ^ c.charCodeAt(0), 16777619) >>> 0;
  Math.random = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };
  const strategy = redteam.Strategies.find(s => s.id === id);
  const tests = await strategy.action([{vars: {prompt: text}, metadata: {pluginId: 'intent'}, assert: []}], 'prompt', {});
  return tests.map(t => t.vars.prompt).filter(t => typeof t === 'string');
}
(async () => {
  const request = JSON.parse(fs.readFileSync(0, 'utf8'));
  if (request.action === 'catalog') {
    const transforms = [];
    const failures = [];
    for (const id of localIds) {
      try {
        const output = await transform(id, 'AEGIS library integration test');
        if (!output.length) throw new Error('No text result');
        transforms.push({id: 'promptfoo:' + id, framework: 'promptfoo', name: id, version,
          implementation: 'redteam.Strategies.action', license: 'MIT', local: true});
      } catch(e) { failures.push({id, error: e.message}); }
    }
    process.stdout.write(JSON.stringify({transforms, resources: [], failures}));
  } else if (request.action === 'transform') {
    const outputs = await transform(request.id.replace(/^promptfoo:/, ''), request.text);
    process.stdout.write(JSON.stringify({outputs, version, framework: 'promptfoo'}));
  } else throw new Error('Unknown action');
})().catch(e => { process.stderr.write(e.message + '\n'); process.exitCode = 1; });
