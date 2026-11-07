import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const workspaceDir = 'C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform';
const runtimeRoot = 'C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const SKILL_DIR = 'C:/Users/Admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
process.env.RUNTIME_NODE_MODULES = runtimeRoot + '/node/node_modules';
process.env.RUNTIME_BIN_DIR = runtimeRoot + '/bin/override';
const RUNTIME_PYTHON = runtimeRoot + '/python/python.exe';
const { Presentation, PresentationFile, FileBlob } = await import(pathToFileURL(
  runtimeRoot + '/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const { finalizePresentation } = await import(pathToFileURL(
  SKILL_DIR + '/container_tools/artifact_tool_utils.mjs').href);

const buildDir = path.join(workspaceDir, 'artifacts/presentation-build/private');
const outputDir = path.join(workspaceDir, 'artifacts/presentation-build/output');
await fs.mkdir(buildDir, {recursive:true});
await fs.mkdir(outputDir, {recursive:true});
const finalPath = path.join(outputDir, 'Quy_trinh_cai_dat_MekoDataCTF_v3.pptx');
const presentation = Presentation.create({slideSize:{width:1280,height:720}});
const slide = presentation.slides.add();
slide.background.fill = '#F7F9FC';

function text(value, x, y, width, height, size, color='#15283E', bold=false) {
  const shape = slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width,height},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;
  shape.text.style={typeface:'Arial',fontSize:size,color,bold,wrap:'square',autoFit:'none',insets:0,verticalAlignment:'top'};
  return shape;
}
text('Quy trình cài đặt và tạo bài thi',64,38,1152,66,46,'#102B46',true);
text('MekoDataCTF  ·  CyberRangeCZ + ForcAD',66,108,1148,38,25,'#50667D');

const values = [
  ['Giai đoạn','Công việc chính','Khả năng tái sử dụng'],
  ['01–03\nCài nền tảng','Cài công cụ, website và ForcAD;\nkhởi tạo cấu hình và tài khoản.','Dùng lại nền tảng;\nđổi cấu hình nơi chạy.'],
  ['04\nChốt đội trên website','Chốt số lượng, tên kỹ thuật và IP;\nxuất danh sách vào lab.json.','Dùng lại công cụ;\ntạo riêng danh sách đội.'],
  ['05–06\nChuẩn bị gói bài','Nhận app/checker; cấu hình máy,\nmạng và cách cài đặt lên VM.','Dùng lại khung; tạo riêng\nnội dung đề và logic checker.'],
  ['07–08\nCấp phát môi trường','Git → định nghĩa sandbox → pool;\nallocate, lấy SSH và nối agent.','Dùng lại quy trình; cấu hình\nmôi trường và quyền truy cập.'],
  ['09–10\nKết nối chấm điểm','Thêm adapter/profile, ghép đội;\nđồng bộ token và chạy collector.','Dùng lại giao vận;\nchỉnh cấu hình tích hợp.'],
  ['11–12\nNghiệm thu, mở thi','Thử check–put–get, nộp flag;\nchuẩn bị dữ liệu sạch rồi mở thi.','Dùng lại khung kiểm thử;\ntạo riêng dữ liệu và hồ sơ.'],
];
const table = slide.tables.add({rows:values.length,columns:3,left:64,top:164,width:1152,height:444,columnWidths:[254,520,378],values});
table.borders.assign({style:'solid',fill:'#D5E0EC',width:1});
table.styleOptions={headerRow:true,bandedRows:false};
for(let r=0;r<values.length;r++) {
  table.rows[r].height = r===0 ? 48 : 66;
  for(let c=0;c<3;c++) {
    const cell=table.getCell(r,c);
    cell.fill=r===0?'#153B59':(r%2===0?'#EDF3F8':'#FFFFFF');
    cell.text.style={typeface:'Arial',fontSize:r===0?24:23,color:r===0?'#FFFFFF':(c===2?'#146A64':'#15283E'),bold:r===0||c===0,wrap:'square',autoFit:'none',verticalAlignment:'middle'};
  }
}
text('Nền tảng dùng chung  /  Cấu hình theo bài  /  Nội dung và dữ liệu tạo riêng',66,631,1148,32,23,'#146A64',true);
text('Phạm vi: CyberRangeCZ đã có sẵn. Hiện round1 và meko_boutique có profile ForcAD.',66,675,1148,27,20,'#52657A');

const reportPath=path.join(workspaceDir,'docs/QUY-TRINH-CAI-DAT-TONG-QUAT-BAO-CAO.md');
const report=await fs.readFile(reportPath,'utf8');
slide.speakerNotes.text='Nguồn nội bộ: '+reportPath+'\n\n'+
  'Đối chiếu mã nguồn ngày 07/11/2026. Các kết luận là phân tích source, chưa xác nhận nghiệm thu pool thực tế.\n'+
  'Nguồn CyberRangeCZ: https://docs.platform.cyberrange.cz/basic-concepts/typical-training-workflow/training-workflow-cloud/\n'+
  'https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/pool/\n\n'+report;

const candidatePath=path.join(buildDir,'candidate-04.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
console.log('Draft exported.');
const result=await finalizePresentation({workspaceDir,candidatePath,finalPath,
  pythonExecutable:RUNTIME_PYTHON,
  integrityValidatorPath:SKILL_DIR+'/container_tools/inspect_presentation_package_integrity.py',
  layoutValidatorPath:SKILL_DIR+'/container_tools/inspect_presentation_layout_geometry.py',
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--require-native-table-slide','1'],
  explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[1],requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,
  receiptPath:path.join(buildDir,'validation-v3.json')});
console.log('Finalized:',JSON.stringify({finalPath:result.finalPath,byteCount:result.byteCount,sha256:result.finalSha256,integrity:result.packageIntegrity.status,layoutFindings:result.presentationLayout.findingCount}));
const finalDeck=await PresentationFile.importPptx(await FileBlob.load(finalPath));
const png=await finalDeck.export({slide:finalDeck.slides.items[0],format:'png',scale:1});
await fs.writeFile(path.join(buildDir,'slide-01.png'),new Uint8Array(await png.arrayBuffer()));
console.log('Preview:',path.join(buildDir,'slide-01.png'));
console.log('PPTX:',finalPath);
