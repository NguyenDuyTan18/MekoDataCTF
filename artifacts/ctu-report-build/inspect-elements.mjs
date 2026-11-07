import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {Presentation}=await import(pathToFileURL('C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const p=Presentation.load(JSON.parse(await fs.readFile('artifacts/ctu-report-build/imported-model.json','utf8')));
const data=await p.inspect({select:'$.slides[1].elements[*]',include:['id','type','text']});
console.log(JSON.stringify(data).slice(0,2500));
console.log('keys',Object.keys(p.toProto()), 'slidekeys',Object.keys(p.toProto().slides[1]));
console.log('proto-small',JSON.stringify(p.toProto().slides[1]).slice(0,1500));
