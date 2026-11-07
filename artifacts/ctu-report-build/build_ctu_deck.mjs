import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const root='C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform';
const runtime='C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const skill='C:/Users/Admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
process.env.RUNTIME_NODE_MODULES=runtime+'/node/node_modules';
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const build=path.join(root,'artifacts/ctu-report-build');
const temp=path.join(build,'private');
await fs.mkdir(temp,{recursive:true});
const sourcePath=path.join(build,'source-template.pptx');
const sourceHash=createHash('sha256').update(await fs.readFile(sourcePath)).digest('hex');
const original=(await PresentationFile.importPptx(await FileBlob.load(sourcePath))).toProto();
const sourceIndices=[0,1,2,3,4,5,6,7,22,23,25];
const standard=original.slides[1];
const ornaments=standard.elements.slice(0,3);
const proto={...original,slides:sourceIndices.map(i=>structuredClone(original.slides[i]))};
for(let i=1;i<proto.slides.length-1;i++){
  proto.slides[i].elements=structuredClone(ornaments);
  proto.slides[i].useLayoutId=standard.useLayoutId;
  proto.slides[i].index=i;
}
proto.slides.forEach((s,i)=>s.index=i);
const deck=Presentation.load(proto);
const C={blue:'#0070C0',ink:'#173B50',line:'#1598F2',pale:'#E9F3FA',green:'#008878',orange:'#C36B00'};
const word='report/Quy_trinh_trien_khai_va_van_hanh_MekoDataCTF.docx';
const sourceNotes='Nội dung: '+word+'. Mẫu trình bày: D:/Subject/LuanVan/Bao_cao_Tuan4_Attack_Defense.pptx. Các kết luận kỹ thuật dựa trên mã nguồn ngày 07/11/2026.';

function text(s,val,x,y,w,h,size=29,color=C.ink,bold=false,align='left'){
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=val;sh.text.style={typeface:'Times New Roman',fontSize:size,color,bold,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0};return sh;
}
function setup(index,title,notes=''){
  const s=deck.slides.items[index];
  const t=s.shapes.items.find(x=>x.id==='4');
  t.text=title;
  t.text.style={typeface:'Times New Roman',fontSize:42.6667,color:C.blue,bold:true,verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:2};
  s.speakerNotes.text=sourceNotes+'\n\n'+notes;
  return s;
}
function table(s,headers,rows,widths,{y=170,rowH=86,font=27}={}){
  const vals=[headers,...rows];
  const t=s.tables.add({rows:vals.length,columns:headers.length,left:64,top:y,width:1152,height:50+rows.length*rowH,columnWidths:widths,values:vals});
  t.borders.assign({style:'solid',fill:'#FFFFFF',width:1});t.styleOptions={headerRow:true,bandedRows:false};
  for(let r=0;r<vals.length;r++){
    t.rows[r].height=r?rowH:50;
    for(let c=0;c<headers.length;c++){
      const cell=t.getCell(r,c);cell.fill=r===0?C.blue:(r%2===0?'#EDF5FA':'#FFFFFF');
      cell.text.style={typeface:'Times New Roman',fontSize:r===0?27:font,color:r===0?'#FFFFFF':C.ink,bold:r===0||c===0,verticalAlignment:'middle',autoFit:'none',wrap:'square'};
    }
  }return t;
}
function node(s,label,x,y,w=270,h=106,{color=C.line,fill=C.pale,size=25,geometry='rect'}={}){
  const sh=s.shapes.add({geometry,position:{left:x,top:y,width:w,height:h},fill,line:{fill:color,width:1.3}});
  sh.text=label;sh.text.style={typeface:'Times New Roman',fontSize:size,color:C.ink,alignment:'center',verticalAlignment:'middle',wrap:'square',autoFit:'none',insets:8};return sh;
}
function connect(s,a,b,fromSide='right',toSide='left',{color=C.line,both=false,kind='straight'}={}){
  return s.shapes.connect(a,b,{kind,fromSide,toSide,line:{fill:color,width:1.8},head:{type:both?'triangle':'none',width:'sm',length:'sm'},tail:{type:'triangle',width:'sm',length:'sm'}});
}

// Reuse the original CTU cover and author block; change only the report subject.
{
  const s=deck.slides.items[0];
  const topic=s.shapes.items.find(x=>String(x.text).startsWith('Nghiên cứu'));
  topic.text='Quy trình triển khai và vận hành bài thi\nAttack–Defense trên CyberRangeCZ và ForcAD';
  topic.text.style={typeface:'Times New Roman',fontSize:31,color:'#FFFFFF',alignment:'center',verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:0};
  s.speakerNotes.text=sourceNotes+'\nGiữ thông tin giảng viên, sinh viên và đơn vị từ trang bìa mẫu CTU.';
}
{
  const s=setup(1,'Nội dung');
  [
    '1. Quy trình triển khai tổng thể',
    '2. Chuẩn bị bài và cấp phát môi trường',
    '3. Tích hợp ForcAD và quyền truy cập',
    '4. Nghiệm thu và mở cuộc thi',
    '5. Phần tái sử dụng và cách bật lại dự án',
  ].forEach((x,i)=>text(s,x,127,151+i*84,1080,56,33,'#222222',true));
}
{
  const s=setup(2,'Quy trình triển khai tổng thể','Luồng 12 bước theo Word. Chốt đội đi trước chuẩn bị topology. Ansible chạy trong cấp phát. Kiểm tra từ tài khoản thí sinh sau cấu hình Training trước mở thi. Sơ đồ dùng shape và connector gắn với nhau để có thể chỉnh sửa.');
  const labels=[
    '1. Chốt đội\nTên, số lượng và IP',
    '2. Soạn gói bài\nỨng dụng và checker',
    '3. Soạn cấu hình\nTopology và Ansible',
    '4. Git và định nghĩa\nURL cùng revision',
    '5. Tạo pool\nChọn định nghĩa',
    '6. Allocate\nTạo VM và cài dịch vụ',
    '7. Lấy truy cập\nTách quyền BTC và đội',
    '8. Cấu hình ForcAD\nAdapter và collector',
    '9. Ghép đội\nĐồng bộ token',
    '10. Thi thử\nKiểm tra chấm điểm',
    '11. Training\nXác minh quyền VM',
    '12. Mở thi\nBắt đầu round và tick',
  ];
  const boxes=[];
  for(let i=0;i<12;i++){
    const r=Math.floor(i/4),c=r%2?3-i%4:i%4;
    boxes.push(node(s,labels[i],50+c*302,160+r*158,270,106,i===11?{color:C.green,fill:'#EBF7F3'}:{}));
  }
  for(let i=0;i<11;i++){
    if(i===3||i===7)connect(s,boxes[i],boxes[i+1],'bottom','top');
    else if(Math.floor(i/4)%2)connect(s,boxes[i],boxes[i+1],'left','right');
    else connect(s,boxes[i],boxes[i+1]);
  }
  text(s,'Gói bài → Môi trường → Tích hợp → Nghiệm thu → Mở thi',66,619,1148,43,27,C.blue,true,'center');
}
{
  const s=setup(3,'Chuẩn bị đội và gói bài','Bước 1 đến 3. Website lấy toàn bộ đội khi export, cần lọc/đối chiếu danh sách chính thức. Ứng dụng có thể chung source nhưng mỗi đội cần dữ liệu và instance riêng. Cấu hình không tự đồng bộ giữa lab.json, topology và provisioning.');
  table(s,['Bước','Công việc','Kết quả'],[
    ['1. Chốt đội','Tên kỹ thuật, số lượng;\nánh xạ đội với VM và IP.','Danh sách chính thức\nvà lab.json.'],
    ['2. Gói nội dung','Ứng dụng, dữ liệu, task,\nchecker và hướng dẫn.','Gói bài có\nphiên bản xác định.'],
    ['3. Cấu hình VM','Topology và playbook\ncài dịch vụ, tài khoản, agent.','Sandbox Definition\nsẵn sàng triển khai.'],
  ],[235,510,407],{rowH:96,font:27});
  text(s,'Checker phải đáp ứng: check · put · get',66,557,1148,48,32,C.blue,true,'center');
  text(s,'Dùng lại khung; nội dung đề và logic checker được chuẩn bị riêng.',66,620,1148,38,27,'#333333',false,'center');
}
{
  const s=setup(4,'Git và cấp phát môi trường','Bước 4 đến 7. Nguồn: https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/pool/ và https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/. Pool giữ revision khi tạo. Không coi bộ management key là quyền thí sinh.');
  table(s,['Bước','Thao tác','Cần xác nhận'],[
    ['4. Git và định nghĩa','Đăng ký Git URL\nvà revision trên Portal.','Đúng cấu trúc gốc\nvà phiên bản bài.'],
    ['5. Tạo pool','Chọn Sandbox Definition\nvà số sandbox.','Số sandbox khác\nsố VM đội.'],
    ['6. Allocate','Tạo VM, mạng;\nchạy Ansible provisioning.','Dịch vụ và checker\nđược cài thành công.'],
    ['7. Truy cập','BTC lấy SSH quản trị;\nđội nhận quyền máy riêng.','Không phát management\nkey cho thí sinh.'],
  ],[250,510,392],{rowH:88,font:26});
  text(s,'Thay Git không tự cập nhật các VM đang chạy.',66,615,1148,42,29,C.blue,true,'center');
}
{
  const s=setup(5,'Luồng kết nối ForcAD và website','Bước 8 và 9. Website giao tiếp API với ForcAD. Engine gọi adapter, RPC JSON và collector; collector SSH tới agent trên VM checker; agent truy cập dịch vụ đội. Các mũi tên hai chiều thể hiện yêu cầu và phản hồi. Token website được đồng bộ sang đội ForcAD đã tồn tại.');
  const engine=node(s,'ForcAD\nĐiều phối và tính điểm',74,160,300,92);
  const adapter=node(s,'Adapter và RPC\nWrapper từng task',490,160,300,92);
  const collector=node(s,'Collector\nChọn đúng MEKO_LAB',906,160,300,92);
  const website=node(s,'Website\nĐội, nộp flag, bảng điểm',74,346,300,92,{color:C.green,fill:'#EBF7F3'});
  const service=node(s,'Dịch vụ các đội\nDữ liệu riêng từng đội',490,346,300,92);
  const agent=node(s,'VM checker\nAgent và logic kiểm tra',906,346,300,92);
  connect(s,engine,adapter,'right','left',{both:true});connect(s,adapter,collector,'right','left',{both:true});
  connect(s,engine,website,'bottom','top',{both:true});connect(s,collector,agent,'bottom','top',{both:true});connect(s,agent,service,'left','right',{both:true});
  text(s,'API',238,287,95,34,24,C.green,true);text(s,'SSH',1068,287,95,34,24,C.blue,true);
  text(s,'lab.json: đội/IP, task, SSH và lệnh agent',70,490,1136,44,28);
  text(s,'Profile: đường dẫn checker, flag, tick và timeout',70,539,1136,44,28);
  text(s,'Website: ghép đúng đội và đồng bộ token sang ForcAD',70,588,1136,44,28);
}
{
  const s=setup(6,'Training và quyền truy cập','Bước 11. Tạo Training Definition, Instance, thời gian truy cập và gán pool. Nguồn: https://docs.platform.cyberrange.cz/user-guide-basic/training-agenda/training-instance/ và https://docs.platform.cyberrange.cz/user-guide-advanced/trainings/trainings-overview/. Training Run nhận sandbox; không có quy tắc mọi đội phải dùng chung một tài khoản. Với nhiều đội chung sandbox phải kiểm tra quyền VM theo đội.');
  text(s,'Training Definition → Training Instance → Gán pool → Cấp quyền',66,139,1148,50,28,C.blue,true,'center');
  table(s,['Thông tin','Mục đích'],[
    ['Tài khoản Portal','Xác thực người dùng vào CyberRangeCZ.'],
    ['Token Training','Vào đợt training được cấp.'],
    ['Token đội','Nhận diện đội và nộp flag qua website/ForcAD.'],
    ['SSH hoặc GUI','Đăng nhập đúng VM với quyền được cấp.'],
  ],[345,807],{y:211,rowH:60,font:27});
  text(s,'Một Training Run nhận một sandbox.',66,528,1148,43,32,C.blue,true,'center');
  text(s,'Sandbox nhiều đội vẫn phải phân quyền VM.\nThử truy cập bằng tài khoản thí sinh trước khi mở thi.',66,581,1148,75,28,C.ink,false,'center');
}
{
  const s=setup(7,'Nghiệm thu và mở cuộc thi','Bước 10 đến 12. Kiểm tra check, put, get, nộp flag, điểm, timing và quyền thí sinh. Không mở thi nếu chưa đạt. Sau thi thử lưu hồ sơ và chuẩn bị dữ liệu sạch. Website/Training chưa tự điều khiển bắt đầu round ForcAD.');
  const trial=node(s,'Chạy thi thử\nKiểm tra toàn bộ luồng',80,202,280,102);
  const gate=node(s,'Đạt yêu cầu?',459,172,220,162,{geometry:'diamond',color:C.orange,fill:'#FFF4E7',size:27});
  const start=node(s,'Chuẩn bị dữ liệu sạch\nBTC mở round ForcAD',837,202,360,102,{color:C.green,fill:'#EBF7F3',size:27});
  const fix=node(s,'Chỉnh cấu hình hoặc checker\nKiểm tra lại trên môi trường',391,432,356,106,{color:C.orange,fill:'#FFF4E7',size:26});
  connect(s,trial,gate);connect(s,gate,start,'right','left',{color:C.green});
  connect(s,gate,fix,'bottom','top',{color:C.orange});
  connect(s,fix,trial,'left','bottom',{color:C.orange,kind:'elbow'});
  text(s,'Đạt',726,220,84,38,25,C.green,true);text(s,'Chưa đạt',603,365,150,38,25,C.orange,true);
  text(s,'Nghiệm thu: dịch vụ, check–put–get, flag, điểm, thời gian và quyền truy cập.',66,596,1148,70,28,C.ink,false,'center');
}
{
  const s=setup(8,'Phần tái sử dụng và phần tạo riêng','Giữ cơ chế nền tảng khi tương thích. Cấu hình lại topology, provisioning, profile, adapter và Training. Nội dung nghiệp vụ, logic checker, danh sách đội, credential và trạng thái sạch cần được xác nhận cho bài hoặc đợt mới. Source hiện chỉ có profile round1 và meko_boutique.');
  table(s,['Phân loại','Thành phần','Cách thực hiện'],[
    ['Dùng lại','Website, engine,\ngiao vận tương thích.','Giữ cơ chế chung;\nkiểm tra điều kiện áp dụng.'],
    ['Cấu hình lại','Topology, Ansible, lab config,\nprofile, adapter, Training.','Thay thông số và chỉnh\ngiả định theo bài.'],
    ['Tạo riêng','Nội dung đề, lỗ hổng, dữ liệu,\nlogic checker và quyền đội.','Không dùng nguyên trạng\ncho bài thi khác.'],
  ],[230,490,432],{y:177,rowH:112,font:27});
  text(s,'Hiện round1 và meko_boutique có profile ForcAD.',66,596,1148,43,29,C.blue,true,'center');
}
{
  const s=setup(9,'Bật lại bài thi đã được cài','Áp dụng khi nền tảng và sandbox đã được chuẩn bị. Không tạo lại pool hoặc seed database như bước khởi động thông thường. Tài liệu Word có phụ lục cài nền tảng. Khi dừng dùng dashboard trước, dừng collector/website rồi docker compose stop.');
  [
    ['1. Sandbox','Xác nhận môi trường và dịch vụ hoạt động.'],
    ['2. ForcAD','Chạy docker compose up -d trong thư mục engine.'],
    ['3. Website','Chạy npm start ở terminal riêng.'],
    ['4. Collector','Chọn MEKO_LAB và chạy collector đúng bài.'],
    ['5. Cuộc thi','Kiểm tra trạng thái cũ trước khi tiếp tục hoặc mở lượt mới.'],
  ].forEach(([a,b],i)=>{text(s,a,95,151+i*86,270,43,30,C.blue,true);text(s,b,365,151+i*86,820,64,29);});
  text(s,'BTC phối hợp riêng lịch website, thời gian Training và tick ForcAD.',66,615,1148,46,27,C.ink,true,'center');
}
deck.slides.items[10].speakerNotes.text=sourceNotes;

const candidate=path.join(temp,'candidate.pptx');
const finalPath=path.join(root,'report/Quy_trinh_trien_khai_MekoDataCTF_CTU.pptx');
await (await PresentationFile.exportPptx(deck)).save(candidate);
const tableOwners=[4,5,7,9];
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,
  pythonExecutable:runtime+'/python/python.exe',
  integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
  layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tableOwners.flatMap(x=>['--require-native-table-slide',String(x)])],
  explicitTotalSlideCount:11,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'reference',families:['Times New Roman','Calibri','Readex Pro'],referencePath:sourcePath,referenceSha256:sourceHash},
  verifyArtifactToolImport:true,receiptPath:path.join(temp,'validation.json')});
console.log(JSON.stringify({finalPath:result.finalPath,slides:11,integrity:result.packageIntegrity.status,layout:result.presentationLayout.findingCount}));
const rendered=await PresentationFile.importPptx(await FileBlob.load(finalPath));
for(let i=0;i<rendered.slides.items.length;i++){
  const png=await rendered.export({slide:rendered.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(temp,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
  console.log('Rendered',i+1);
}
