import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root='C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform';
const build=root+'/artifacts/pptx-review/build';
const SKILL='C:/Users/Admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
const source=root+'/report/Quy_trinh_trien_khai_MekoDataCTF_CTU.pptx';
const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs'));
const referenceSha256=crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex');
try {
const result=await finalizePresentation({
 workspaceDir:root,candidatePath:build+'/candidate.pptx',finalPath:root+'/report/Quy_trinh_trien_khai_MekoDataCTF_CTU_Chi_tiet.pptx',
 explicitTotalSlideCount:25,requiredNativeTableOwnerSlides:[23],requiredNativeChartOwnerSlides:[],
 pythonExecutable:'C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','23'],
 fontPolicy:{basis:'reference',families:['Times New Roman','Calibri','Readex Pro'],referencePath:source,referenceSha256},
 verifyArtifactToolImport:true,receiptPath:build+'/validation.json'
});
console.log(JSON.stringify(result));
}catch(e){console.log(e.message);if(e.details)console.log(JSON.stringify(e.details));process.exitCode=1;}
