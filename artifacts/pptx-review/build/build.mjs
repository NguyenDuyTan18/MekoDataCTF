import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root='C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform';
const build=root+'/artifacts/pptx-review/build';
const SKILL='C:/Users/Admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
const RUNTIME_PYTHON='C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const source=root+'/report/Quy_trinh_trien_khai_MekoDataCTF_CTU.pptx';
const final=root+'/report/Quy_trinh_trien_khai_MekoDataCTF_CTU_Chi_tiet.pptx';
const {importRuntimeModule}=await import(pathToFileURL(SKILL+'/container_tools/runtime_helpers.mjs'));
const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs'));
const {FileBlob,PresentationFile}=await importRuntimeModule('@oai/artifact-tool');
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const original=[...p.slides.items];
const content=JSON.parse(await fs.readFile(build+'/content.json','utf8'));
const blue='#0070C0',ink='#173E53';
function text(slide,name,value,x,y,w,h,size=28,bold=false,color=ink) {
 const s=slide.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=value;
 s.text.style={fontFamily:'Times New Roman',fontSize:size,bold,color,alignment:'left',verticalAlignment:'top',wrap:true};
 s.text.insets=0;
 return s;
}
function header(slide,title) {
 const s=slide.shapes.items.find(x=>x.name==='TextBox 3');
 s.position={left:86.4,top:17.28,width:1125,height:67};
 s.text=title;
 s.text.style={fontFamily:'Times New Roman',fontSize:44,bold:true,color:blue,wrap:false};
 s.text.insets=0;
}
function detailed(item) {
 const s=original[1].duplicate();
 for(const x of [...s.shapes.items]) if(!['2','3','4'].includes(x.id))x.delete();
 header(s,item.title);
 text(s,'input','Đầu vào: '+item.input,70,112,1130,64,27);
 text(s,'operations','Thao tác triển khai',70,184,1130,40,29,true,blue);
 item.actions.forEach((v,i)=>text(s,'action-'+(i+1),(i+1)+'. '+v,85,235+i*77,1105,70,28));
 text(s,'completion-label','Điều kiện hoàn thành',70,557,1130,40,29,true,blue);
 text(s,'completion',item.done,70,602,1130,61,27);
 s.speakerNotes.text=item.notes;
 return s;
}
const prep=content.preparation.map(detailed);
const steps=content.steps.map(detailed);
const ops=content.operation.map(detailed);

// Keep the original university design, logos, cover and native diagrams.
// Repair a narrow inherited text frame so the template's CTU footer stays on one line.
for(const layout of p.layouts.items) {
 for(const shape of layout.shapes?.items??[]) {
  if(String(shape.text).trim()==='CTU') {
   shape.text.style={fontFamily:'Times New Roman',fontSize:23,bold:true,color:'#FFFFFF',wrap:false,alignment:'center',verticalAlignment:'middle'};
   shape.text.insets=0;
  }
 }
}
for(const shape of original[0].shapes.items) {
 const q=shape.position;
 if(q.left+q.width>1270)shape.position={...q,width:1270-q.left};
}

const agenda=original[1];
header(agenda,'Nội dung');
const agendaText=[
 '1. Điều kiện và cài nền tảng lần đầu',
 '2. Sơ đồ tổng thể và 12 bước triển khai chi tiết',
 '3. Thi thử, quyền thí sinh và mở cuộc thi',
 '4. Giám sát, kết thúc và khôi phục môi trường',
 '5. Tái sử dụng và bật lại hệ thống'
];
agenda.shapes.items.filter(x=>/^Rectangle [4-8]$/.test(x.name)).forEach((x,i)=>{x.text=agendaText[i];});

const architecture=original[5];
header(architecture,'Các thành phần cần kết nối');
const replacements={
 'Adapter và RPC\nWrapper từng task':'Bộ chuyển tiếp\nYêu cầu kiểm tra',
 'Collector\nChọn đúng MEKO_LAB':'Collector\nKết nối đúng môi trường',
 'VM checker\nAgent và logic kiểm tra':'VM checker\nKiểm tra dịch vụ đội',
 'lab.json: đội/IP, task, SSH và lệnh agent':'Thông tin triển khai: đội, IP, task và đường truy cập checker',
 'Profile: đường dẫn checker, flag, tick và timeout':'Thiết lập chấm: lịch tick, tuổi flag và thời hạn xử lý',
 'Website: ghép đúng đội và đồng bộ token sang ForcAD':'Website: ghép đúng đội và đồng bộ token trước khi thi'
};
for(const x of architecture.shapes.items){const v=replacements[String(x.text)];if(v)x.text=v;}
architecture.speakerNotes.text='Sơ đồ thành phần để người triển khai xác định điểm kiểm tra kết nối. Hướng dẫn thao tác cụ thể ở bước 8–10. Nguồn: slide 6 bản gốc, docs/LUONG-CAC-FILE.md và tài liệu quy trình tổng quát.';

const overview=original[2];
header(overview,'Quy trình triển khai tổng thể');
text(overview,'detail-reference','12 bước tương ứng 12 slide chi tiết, từ slide 8 đến slide 19',70,103,1130,37,27,true,blue);
for(const x of overview.shapes.items){
 const value=String(x.text);
 if(value==='3. Soạn cấu hình\nTopology và Ansible')x.text='3. Soạn cấu hình\nMáy, mạng và cài đặt';
 if(value==='4. Git và định nghĩa\nURL cùng revision')x.text='4. Git và định nghĩa\nKho và phiên bản';
 if(value==='8. Cấu hình ForcAD\nAdapter và collector')x.text='8. Cấu hình ForcAD\nKết nối checker';
 if(value==='10. Thi thử\nKiểm tra chấm điểm')x.text='10. Thi thử\nNghiệm thu kỹ thuật';
 if(value==='11. Training\nXác minh quyền VM')x.text='11. Training\nThử quyền thí sinh';
 if(value.startsWith('Gói bài →')) x.text='Sau bước 11: xác nhận quyền thí sinh trước khi mở thi';
}
overview.speakerNotes.text='Mỗi ô đánh số 1–12 có đúng một slide chi tiết tương ứng ở slide 8–19. Điều kiện/cài nền tảng lần đầu ở slide 3–5. Vận hành sau khi mở thi ở slide 20–22. Bước 10 nghiệm thu kỹ thuật, bước 11 nghiệm thu bằng tài khoản thí sinh trước khi mở thi. Sơ đồ mô tả quy trình tổ chức một bài trên nền tảng đã cài, không phải cài cả cụm cloud.';

const reuse=original[8];
header(reuse,'Phần tái sử dụng và phần chuẩn bị riêng');
const table=reuse.tables.items[0];
const rows=[
 ['Dùng lại','Website, engine và cơ chế\nkết nối đã nghiệm thu.','Giữ nền tảng, xác nhận\nđiều kiện áp dụng.'],
 ['Cấu hình lại','Đội/IP, máy/mạng, quyền\ntruy cập và thiết lập chấm.','Đối chiếu cấu hình\ngiữa các thành phần.'],
 ['Chuẩn bị riêng','Nội dung bài, dữ liệu sạch,\nchecker và hướng dẫn đội.','Chốt phiên bản và\nnghiệm thu cho bài mới.']
];
rows.forEach((row,r)=>row.forEach((v,c)=>table.cells.set(r+1,c,v)));
reuse.shapes.items.find(x=>x.id==='6').text='Cùng một bài vẫn cần kiểm tra đội, quyền và trạng thái dữ liệu';
reuse.speakerNotes.text='Nguồn: slide 9 bản gốc và mục 3 của tài liệu quy trình tổng quát. Dùng lại nền tảng không đồng nghĩa dùng nguyên trạng dữ liệu, thông tin truy cập hoặc kết quả lượt cũ.';

const restart=original[9];
header(restart,'Bật lại hệ thống đã cài');
const restartDescriptions={
 '6':'Xác nhận VM, đường truy cập và dịch vụ còn hoạt động.',
 '8':'Khởi động dịch vụ engine và kiểm tra dashboard/API.',
 '10':'Khởi động website, thử đăng nhập và kết nối tới engine.',
 '12':'Chọn đúng bài, khởi động collector và thử phản hồi checker.',
 '14':'Xác định tiếp tục lượt cũ hay chuẩn bị lượt mới rồi kiểm tra lại.'
};
for(const x of restart.shapes.items)if(restartDescriptions[x.id])x.text=restartDescriptions[x.id];
restart.shapes.items.find(x=>x.id==='15').text='Bật lại dịch vụ giữ nguyên dữ liệu, khác với chuẩn bị một lượt thi mới';
restart.speakerNotes.text='Hướng dẫn khởi động theo thao tác vận hành, không trình bày lệnh hay mã nguồn. Lịch website, Training và ForcAD cần BTC phối hợp riêng. Nguồn: slide 10 bản gốc và docs/HUONG-DAN-KHOI-DONG.md.';

const thanks=original[10];
thanks.shapes.items.find(x=>x.id==='2').text='CẢM ƠN';
const ordered=[original[0],agenda,...prep,architecture,overview,...steps,...ops,reuse,restart,thanks];
if(ordered.length!==25)throw new Error('Unexpected slide count '+ordered.length);
for(const s of original)if(!ordered.includes(s))s.delete();
ordered.forEach((s,i)=>s.moveTo(i));
const titles=ordered.map((s,i)=>({slide:i+1,title:s.shapes.items.map(x=>String(x.text)).find(x=>x===content.steps[i-7]?.title)||s.shapes.items.find(x=>x.name==='TextBox 3')?.text.toString()||s.shapes.items[0]?.text.toString()}));
await fs.writeFile(build+'/final-order.json',JSON.stringify(titles,null,2));
await fs.mkdir(build+'/final-render',{recursive:true});
for(let i=0;i<ordered.length;i++){
 const png=await p.export({slide:ordered[i],format:'png',scale:1});
 await fs.writeFile(build+'/final-render/slide-'+(i+1)+'.png',new Uint8Array(await png.arrayBuffer()));
 if([0,6,7,17,18,24].includes(i))console.log('rendered',i+1);
}
const candidate=build+'/candidate.pptx';
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log('candidate',candidate);
const referenceSha256=crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex');
const result=await finalizePresentation({
 workspaceDir:root,candidatePath:candidate,finalPath:final,
 explicitTotalSlideCount:25,
 requiredNativeTableOwnerSlides:[23],requiredNativeChartOwnerSlides:[],
 pythonExecutable:RUNTIME_PYTHON,
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','23'],
 fontPolicy:{basis:'reference',families:['Times New Roman','Calibri','Readex Pro'],referencePath:source,referenceSha256},
 verifyArtifactToolImport:true,
 receiptPath:build+'/validation.json'
});
console.log('FINAL',JSON.stringify(result));
