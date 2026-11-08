import fs from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const SKILL='C:/Users/Admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
const {importRuntimeModule}=await import(pathToFileURL(SKILL+'/container_tools/runtime_helpers.mjs'));
const {FileBlob,PresentationFile}=await importRuntimeModule('@oai/artifact-tool');
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform/report/Quy_trinh_trien_khai_MekoDataCTF_CTU.pptx'));
const props=o=>Object.getOwnPropertyNames(Object.getPrototypeOf(o));
console.log('SLIDES',props(p.slides));
console.log('SLIDE',props(p.slides.items[1]));
console.log('SHAPES',props(p.slides.items[1].shapes));
console.log('SHAPE',props(p.slides.items[1].shapes.items[2]));
console.log('TEXT',props(p.slides.items[1].shapes.items[2].text));
console.log('SLIDESIZE',p.slides.items[1].frame);
for(const n of [1,2,3,6,9,10,11]) {
 const s=p.slides.items[n-1];
 console.log('SLIDEDETAIL',n,JSON.stringify(s.shapes.items.map(x=>({id:x.id,name:x.name,position:x.position,text:String(x.text),style:x.text.style}))), 'IMAGES',s.images.items.length,'TABLES',s.tables.items.length);
}
const inspect=await p.inspect({kind:'layout',maxChars:5000});
console.log('LAYOUT',inspect.ndjson);
console.log('MASTERS',p.masters.items.map(x=>({id:x.id,name:x.name})));
await fs.writeFile('C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform/artifacts/pptx-review/build/source.layout.json',await (await p.slides.items[1].export({format:'layout'})).text());
