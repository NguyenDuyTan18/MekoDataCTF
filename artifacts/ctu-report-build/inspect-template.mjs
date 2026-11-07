import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const root='C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform';
const {PresentationFile,FileBlob}=await import(pathToFileURL('C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/artifacts/ctu-report-build/source-template.pptx'));
console.log('imported',p.slides.items.length,'masters',p.masters.items.length,'layouts',p.layouts.items.length);
console.log('slide1-shapes',p.slides.items[0].shapes.items.map(s=>({id:s.id,text:String(s.text),position:s.position})).slice(0,7));
await fs.writeFile(root+'/artifacts/ctu-report-build/imported-model.json',JSON.stringify(p.toProto()));
for(const i of [0,1]){
 const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(root+'/artifacts/ctu-report-build/source-preview/artifact-'+(i+1)+'.png',new Uint8Array(await png.arrayBuffer()));
}
