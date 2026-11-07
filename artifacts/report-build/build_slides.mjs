import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const root='C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform';
const runtime='C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const skill='C:/Users/Admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
process.env.RUNTIME_NODE_MODULES=runtime+'/node/node_modules';
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const temp=path.join(root,'artifacts/report-build/slides-private');
const out=path.join(root,'report/Quy_trinh_trien_khai_MekoDataCTF_Tom_tat.pptx');
await fs.mkdir(temp,{recursive:true});
await fs.mkdir(path.dirname(out),{recursive:true});
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const source='Nguồn nội bộ: report/Quy_trinh_trien_khai_va_van_hanh_MekoDataCTF.docx; docs/QUY-TRINH-CAI-DAT-TONG-QUAT-BAO-CAO.md. Đối chiếu source ngày 07/11/2026.';
const navy='#173B57', ink='#142B42', muted='#526A80', teal='#146B65';

function txt(slide,value,x,y,w,h,size=28,color=ink,bold=false){
  const a=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  a.text=value;a.text.style={typeface:'Arial',fontSize:size,color,bold,wrap:'square',autoFit:'none',insets:0,verticalAlignment:'top'};return a;
}
function slide(title,notes=''){
  const s=deck.slides.add();s.background.fill='#F7F9FC';
  txt(s,title,64,44,1152,72,44,navy,true);
  txt(s,String(deck.slides.items.length).padStart(2,'0'),1154,670,62,28,20,muted);
  s.speakerNotes.text=source+'\n\n'+notes;return s;
}
function table(s,headers,rows,widths,{y=168,rowH=80,font=25}={}){
  const vals=[headers,...rows], height=50+rows.length*rowH;
  const t=s.tables.add({rows:vals.length,columns:headers.length,left:64,top:y,width:1152,height,columnWidths:widths,values:vals});
  t.styleOptions={headerRow:true,bandedRows:false};
  t.borders.assign({style:'solid',fill:'#D7E1EB',width:1});
  for(let r=0;r<vals.length;r++){
    t.rows[r].height=r===0?50:rowH;
    for(let c=0;c<headers.length;c++){
      const cell=t.getCell(r,c);cell.fill=r===0?navy:(r%2===0?'#EDF3F8':'#FFFFFF');
      cell.text.style={typeface:'Arial',fontSize:r===0?25:font,color:r===0?'#FFFFFF':ink,bold:r===0||c===0,wrap:'square',autoFit:'none',verticalAlignment:'middle'};
    }
  }return t;
}

{
  const s=deck.slides.add();s.background.fill='#F7F9FC';
  txt(s,'Quy trình triển khai\nbài thi Attack Defense',64,95,1150,180,60,navy,true);
  txt(s,'MekoDataCTF  ·  CyberRangeCZ + ForcAD',66,310,1148,46,30,muted);
  txt(s,'Website chốt đội → CyberRangeCZ tạo môi trường\n→ ForcAD điều phối chấm và mở thi',66,430,1148,112,32,teal,true);
  txt(s,'Phạm vi: CyberRangeCZ và cloud đã được cung cấp',66,630,1148,42,24,muted);
  s.speakerNotes.text=source+'\nTài liệu trình bày 12 bước từ danh sách đội đến mở thi, với các điều chỉnh về Training Run, quyền VM và đồng bộ token. Cài nền tảng được mô tả trong phụ lục Word.';
}
{
  const s=slide('01–03  Đội thi và gói bài', 'Bước 1: chốt đội và tên kỹ thuật; công cụ export hiện lấy toàn bộ đội trong database. Bước 2: ứng dụng và checker do tác giả cung cấp, mỗi đội có instance và dữ liệu riêng. Bước 3: viết topology và playbook; Ansible chỉ chạy sau khi VM được tạo.');
  table(s,['Bước','Công việc','Kết quả'],[
    ['01  Chốt đội','Số lượng, tên kỹ thuật,\nánh xạ đội với VM và IP.','Danh sách chính thức\nvà lab.json ban đầu.'],
    ['02  Soạn gói bài','Ứng dụng, dữ liệu, task,\nchecker và hướng dẫn.','Gói nội dung có\nphiên bản xác định.'],
    ['03  Soạn cấu hình','Topology và Ansible cài\ndịch vụ, tài khoản, agent.','Định nghĩa môi trường\nsẵn sàng triển khai.'],
  ],[240,500,412],{rowH:92,font:25});
  txt(s,'Checker cần đủ chức năng: check  ·  put  ·  get',66,560,1148,48,30,teal,true);
  txt(s,'Dùng lại khung triển khai; nội dung đề và logic checker được chuẩn bị riêng.',66,627,1080,50,24,muted);
}
{
  const s=slide('04–07  Git và môi trường CyberRangeCZ', 'Gốc repository Sandbox Definition cần topology.yml và provisioning. Đăng ký Git URL/revision trước khi tạo pool. Một sandbox có thể chứa nhiều VM đội. Tách management access của BTC/collector với user access của đội. Nguồn: https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/pool/ và https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/');
  table(s,['Bước','Thao tác','Điểm cần xác nhận'],[
    ['04  Git và định nghĩa','Đưa source lên Git; đăng ký\nGit URL và revision.','Đúng cấu trúc gốc\nvà phiên bản.'],
    ['05  Tạo pool','Chọn Sandbox Definition\nvà số sandbox cần dùng.','Số sandbox khác\nsố VM đội.'],
    ['06  Allocate','Tạo VM, mạng; chạy\nAnsible provisioning.','Dịch vụ và checker\nđược cài thành công.'],
    ['07  Lấy truy cập','Cấu hình SSH cho hệ thống;\ncấp quyền đội riêng.','Không phát management\nkey cho thí sinh.'],
  ],[260,480,412],{rowH:86,font:24});
  txt(s,'Thay Git không tự cập nhật các VM đang chạy.',66,618,1080,42,27,teal,true);
}
{
  const s=slide('08–09  ForcAD và website', 'ForcAD gọi adapter theo task, dùng RPC qua collector và SSH tới agent. lab.json và profile phải đồng nhất đội/IP/task. Wrapper không thay thế logic checker. Website đồng bộ token sau khi đội engine tồn tại; sync không tạo VM hoặc đội thiếu.');
  txt(s,'ForcAD → adapter → collector → SSH → agent → dịch vụ đội',66,140,1148,58,28,teal,true);
  table(s,['Thành phần','Cấu hình cần có'],[
    ['lab.json','Đội/IP, task, SSH config, máy checker và lệnh agent.'],
    ['Adapter và profile','Wrapper task, prefix, định dạng flag và lịch tick.'],
    ['Giới hạn chấm','Timeout, thời gian check và hạn flag phù hợp quy mô.'],
    ['Website','Ghép đúng đội và đồng bộ token sang ForcAD.'],
    ['Collector','Chạy đúng MEKO_LAB và nạp cấu hình mới.'],
  ],[300,852],{y:222,rowH:66,font:25});
  txt(s,'Checker nằm trong sandbox chưa có nghĩa engine tự gọi được.',66,637,1080,38,24,muted);
}
{
  const s=slide('10  Nghiệm thu toàn bộ luồng', 'Nghiệm thu phải được thực hiện trên đúng phiên bản source/config và pool thật. Test local, SSH thông hoặc các giao diện mở được không thay cho thử chấm xuyên suốt. Sau khi cấu hình Training cần kiểm tra thêm từ tài khoản thí sinh.');
  const items=[
    ['1  Website và engine','Lấy điểm, gửi flag và nhận diện đúng đội.'],
    ['2  Engine và sandbox','Adapter, RPC, collector, SSH và agent hoạt động.'],
    ['3  Vòng đời flag','Thử check–put–get; xử lý flag sai, trùng, hết hạn.'],
    ['4  Kết quả và thời gian','Điểm hiển thị đúng; tick và timeout đủ cho quy mô.'],
  ];
  items.forEach(([a,b],i)=>{txt(s,a,66,174+i*105,1148,43,31,navy,true);txt(s,b,66,220+i*105,1148,44,27);});
  txt(s,'Kết quả nghiệm thu gắn với phiên bản và môi trường được triển khai.',66,638,1080,36,24,teal,true);
}
{
  const s=slide('11  Training và quyền truy cập', 'Tạo hoặc chọn Training Definition, tạo Instance, đặt cửa sổ truy cập, gán pool và cấp quyền/token. Portal account dùng xác thực, Training token dùng vào training; khác token đội và SSH credential. Training Run nhận sandbox từ pool. Trong topology nhiều đội chung sandbox, run riêng có thể nhân bản toàn bộ topology. Tài khoản Portal chung không tự phân quyền VM. Phải thử bằng tài khoản thí sinh. Nguồn: https://docs.platform.cyberrange.cz/user-guide-basic/training-agenda/training-instance/ và https://docs.platform.cyberrange.cz/user-guide-advanced/trainings/trainings-overview/');
  txt(s,'Training Definition → Training Instance → gán pool → cấp quyền',66,140,1148,52,27,teal,true);
  table(s,['Thông tin','Mục đích'],[
    ['Tài khoản Portal','Xác thực người dùng vào CyberRangeCZ.'],
    ['Token Training','Vào đợt training được cấp.'],
    ['Token đội','Đăng nhập đội và nộp flag qua website/ForcAD.'],
    ['SSH hoặc GUI','Đăng nhập đúng VM với quyền được cấp.'],
  ],[350,802],{y:215,rowH:58,font:24});
  txt(s,'Một Training Run nhận một sandbox.',66,529,1148,44,31,navy,true);
  txt(s,'Sandbox nhiều đội vẫn phải phân quyền VM;\nkhông tự động dùng chung một tài khoản trainee.',66,580,1148,82,27);
}
{
  const s=slide('12  Mở thi và bật lại dự án', 'Trước thi chính thức lưu thi thử, đưa dữ liệu về trạng thái đầu và kiểm tra lại. Reset điểm không phục hồi source và database ứng dụng. Lịch website, khoảng truy cập Training và tick ForcAD chưa tự đồng bộ. Khi kết thúc lưu hồ sơ trước khi thu hồi hoặc tái tạo. Bật lại không lặp tạo pool nếu môi trường không đổi.');
  txt(s,'Mở cuộc thi',66,165,520,44,32,navy,true);
  txt(s,'Lưu thi thử và chuẩn bị dữ liệu sạch.\n\nCấp đúng quyền truy cập cho đội.\n\nBắt đầu round trên ForcAD.\n\nKết thúc và lưu hồ sơ.',66,230,540,300,27);
  txt(s,'Bật lại bài đã có',680,165,536,44,32,navy,true);
  txt(s,'Xác nhận sandbox đang hoạt động.\n\nForcAD: docker compose up -d\n\nWebsite: npm start\n\nCollector: chọn đúng MEKO_LAB.',680,230,536,300,27);
  txt(s,'BTC phối hợp riêng lịch website, thời gian Training và tick ForcAD.',66,581,1148,80,29,teal,true);
}
{
  const s=slide('Phần tái sử dụng và phần tạo riêng', 'Khả năng dùng lại được xét khi thay bài và vẫn giữ giao thức được hỗ trợ. Tạo riêng không có nghĩa phải viết lại tất cả source khi tổ chức lại cùng bài. Source hiện chỉ có profile round1 và meko_boutique; fashion_shop/fashion_shop_v2 cần tích hợp riêng.');
  table(s,['Phân loại','Thành phần','Cách thực hiện'],[
    ['Dùng lại','Website, engine,\ngiao vận tương thích.','Giữ cơ chế chung;\nkiểm tra điều kiện áp dụng.'],
    ['Cấu hình lại','Topology, Ansible, lab config,\nprofile, adapter, Training.','Thay thông số và chỉnh\ngiả định theo bài.'],
    ['Tạo riêng','Kịch bản, lỗ hổng, dữ liệu,\nlogic checker và quyền đội.','Cung cấp nội dung đúng đề;\nnghiệm thu trên môi trường mới.'],
  ],[230,470,452],{y:180,rowH:110,font:25});
  txt(s,'Hiện round1 và meko_boutique có profile ForcAD.',66,596,1148,44,29,teal,true);
  txt(s,'Các biến thể Fashion Shop cần bổ sung lớp tích hợp phù hợp.',66,645,1080,34,24,muted);
}

const candidate=path.join(temp,'candidate.pptx');
await (await PresentationFile.exportPptx(deck)).save(candidate);
const owners=[2,3,4,6,8];
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:out,
  pythonExecutable:runtime+'/python/python.exe',
  integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
  layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...owners.flatMap(x=>['--require-native-table-slide',String(x)])],
  explicitTotalSlideCount:8,requiredNativeTableOwnerSlides:owners,requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,
  receiptPath:path.join(temp,'validation.json')});
console.log(JSON.stringify({finalPath:result.finalPath,slides:8,integrity:result.packageIntegrity.status,layoutFindings:result.presentationLayout.findingCount}));
const rendered=await PresentationFile.importPptx(await FileBlob.load(out));
for(let i=0;i<rendered.slides.items.length;i++){
  const png=await rendered.export({slide:rendered.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(temp,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
  console.log('Rendered slide',i+1);
}
