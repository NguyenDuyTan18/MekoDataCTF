from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'report'
OUT.mkdir(exist_ok=True)
TARGET = OUT / 'Quy_trinh_trien_khai_va_van_hanh_MekoDataCTF.docx'
if TARGET.exists():
    raise FileExistsError(TARGET)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(1.8), Cm(1.7)
sec.left_margin, sec.right_margin = Cm(2.2), Cm(2.0)
for name in ['Normal', 'Body Text', 'List Bullet', 'List Number']:
    style = doc.styles[name]
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    style.paragraph_format.space_after = Pt(5)
    style.paragraph_format.line_spacing = 1.08
for name, size in [('Title', 22), ('Subtitle', 12), ('Heading 1', 15), ('Heading 2', 12.5)]:
    st = doc.styles[name]
    st.font.name = 'Times New Roman'
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.font.bold = name != 'Subtitle'
    st.paragraph_format.space_before = Pt(9 if 'Heading' in name else 0)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.keep_with_next = True
footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
run = footer.add_run('Trang ')
run.font.size = Pt(9)
field = OxmlElement('w:fldSimple')
field.set(qn('w:instr'), 'PAGE')
footer._p.append(field)
for style in doc.styles:
    for border in list(style.element.xpath('.//w:pBdr')):
        border.getparent().remove(border)
doc.core_properties.title = 'Quy trình triển khai và vận hành bài thi Attack Defense'
doc.core_properties.subject = 'MekoDataCTF tích hợp CyberRangeCZ và ForcAD'
doc.core_properties.author = ''

def p(text, bold_prefix=None, style=None):
    para = doc.add_paragraph(style=style)
    if bold_prefix and text.startswith(bold_prefix):
        para.add_run(bold_prefix).bold = True
        para.add_run(text[len(bold_prefix):])
    else:
        para.add_run(text)
    return para

def h(text, level=1):
    return doc.add_paragraph(text, style=f'Heading {level}')

def page(title):
    doc.add_page_break()
    h(title)

def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    if widths:
        for c, w in zip(t.columns, widths): c.width = Cm(w)
    for i, val in enumerate(headers): t.rows[0].cells[i].text = val
    for vals in rows:
        cells = t.add_row().cells
        for i, val in enumerate(vals): cells[i].text = str(val)
    for ri, row in enumerate(t.rows):
        trpr = row._tr.get_or_add_trPr()
        no_split = OxmlElement('w:cantSplit'); trpr.append(no_split)
        if ri == 0:
            repeat = OxmlElement('w:tblHeader'); trpr.append(repeat)
        for ci, cell in enumerate(row.cells):
            if widths: cell.width = Cm(widths[ci])
            tcpr = cell._tc.get_or_add_tcPr()
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), '183B56' if ri == 0 else ('F1F5F8' if ri % 2 == 0 else 'FFFFFF'))
            tcpr.append(shading)
            for para in cell.paragraphs:
                para.paragraph_format.space_after = Pt(4)
                para.paragraph_format.space_before = Pt(3)
                para.paragraph_format.line_spacing = 1.0
                for run in para.runs:
                    run.font.name = 'Times New Roman'; run.font.size = Pt(10.5)
                    if ri == 0:
                        run.font.bold = True; run.font.color.rgb = RGBColor(255,255,255)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t

def step(num, title, actions, result, reuse):
    h(f'Bước {num} {title}', 2)
    for item in actions: p(item)
    p('Kết quả: ' + result, 'Kết quả:')
    p('Tái sử dụng: ' + reuse, 'Tái sử dụng:')

def code(lines):
    for line in lines:
        para = doc.add_paragraph()
        para.paragraph_format.space_after = Pt(1)
        para.paragraph_format.line_spacing = 1.0
        r = para.add_run(line); r.font.name = 'Consolas'; r.font.size = Pt(9)

doc.add_paragraph('Quy trình triển khai và vận hành bài thi Attack Defense', 'Title')
doc.add_paragraph('MekoDataCTF tích hợp CyberRangeCZ và ForcAD', 'Subtitle')
p('Tài liệu trình bày quy trình từ danh sách đội đăng ký đến chuẩn bị gói bài, cấp phát môi trường, kết nối chấm điểm và mở cuộc thi. Mỗi bước chỉ rõ phần có thể dùng lại và phần cần cấu hình hoặc tạo riêng cho bài mới.')
h('1 Phạm vi và kiến trúc')
p('CyberRangeCZ và cloud được giả định đã hoạt động và BTC có quyền sử dụng. Cài cụm CyberRangeCZ hoặc OpenStack từ đầu là công việc hạ tầng riêng. Nội dung kịch bản, lỗ hổng và thuật toán checker do tác giả bài cung cấp; tài liệu này quy định cách triển khai và tích hợp chúng.')
table(['Thành phần', 'Nơi chạy và vai trò'], [
    ['Website', 'Node.js trên máy vận hành; quản lý đội, nhận flag và hiển thị điểm.'],
    ['ForcAD', 'Docker trên máy vận hành; quản lý đội và task, điều phối tick, sinh flag và tính điểm.'],
    ['Collector', 'Python trên máy vận hành; chuyển yêu cầu chấm qua SSH đến agent.'],
    ['CyberRangeCZ', 'Tạo VM và mạng, chạy provisioning, quản lý truy cập Training.'],
    ['Dịch vụ và checker', 'Chạy trong sandbox; mỗi đội có dịch vụ và dữ liệu riêng.'],
], [3.0,13.8])
h('2 Cách đọc mức tái sử dụng')
table(['Mức', 'Ý nghĩa'], [
    ['Dùng lại', 'Giữ phần mềm hoặc cơ chế chung nếu giao thức và yêu cầu vẫn phù hợp.'],
    ['Cấu hình lại', 'Giữ khung nhưng thay thông số hoặc chỉnh phần phụ thuộc bài.'],
    ['Tạo riêng', 'Chuẩn bị nội dung, quyền, tài nguyên hoặc dữ liệu phù hợp với bài và đợt thi.'],
], [3.0,13.8])
p('Kết quả đối chiếu dựa trên mã nguồn ngày 07/11/2026. Trước khi mở thi vẫn cần nghiệm thu trên đúng máy vận hành và pool được sử dụng.')

page('3 Chốt đội và chuẩn bị gói bài')
step(1, 'Chốt danh sách đội trên website', [
    'BTC chốt các đội được tham gia, số lượng đội và tên kỹ thuật duy nhất. Tên hiển thị có thể khác tên kỹ thuật; website dùng trường Tên đội trên ForcAD nếu được khai, nếu trống sẽ dùng slug của tên đội.',
    'Lập bảng ánh xạ đội website, tên ForcAD, hostname hoặc alias SSH và IP dịch vụ. Danh sách này phải có trước khi quyết định số VM đội. Công cụ export hiện lấy toàn bộ đội trong database nên cần đối chiếu lại danh sách được tham gia.',
], 'Danh sách đội chính thức và cấu hình lab ban đầu.', 'Dùng lại chức năng website và export; cấu hình lại tên và IP; xác định riêng danh sách đợt thi.')
table(['Website', 'Tên kỹ thuật', 'VM', 'IP ví dụ'], [
    ['Đội A', 'team1', 'team1', '10.90.0.11'], ['Đội B', 'team2', 'team2', '10.90.0.12'],
], [4.0,4.0,4.0,4.8])
step(2, 'Chuẩn bị ứng dụng và checker', [
    'Tác giả bài cung cấp ứng dụng có lỗ hổng, dữ liệu ban đầu, danh sách task, checker, hướng dẫn và tiêu chí nghiệm thu. Có thể dùng một mã nguồn để triển khai cho nhiều đội, nhưng mỗi đội cần instance và dữ liệu riêng.',
    'Checker cần xác định rõ check kiểm tra chức năng dịch vụ, put đặt flag và get xác minh flag đã đặt. Checker chỉ kiểm tra health chưa đủ cho cơ chế chấm flag hiện tại.',
], 'Gói nội dung có phiên bản và giao thức checker được xác định.', 'Dùng lại cách tổ chức gói; tạo riêng kịch bản, lỗ hổng, dữ liệu nghiệp vụ và logic checker của đề khác.')
step(3, 'Chuẩn bị topology và playbook Ansible', [
    'Khai số VM đội, máy checker, router, mạng, IP, image và flavor. Số đội quyết định quy mô nhưng không bắt buộc mỗi đội có mạng riêng.',
    'Viết playbook cài runtime, chép source, tạo tài khoản, dữ liệu, service và agent. Ở bước này mới chuẩn bị file; Ansible được chạy khi VM đã được tạo trong quá trình cấp phát.',
], 'Sandbox Definition đủ thông tin cài môi trường.', 'Dùng lại khung IaC và Ansible; chỉnh danh sách máy, đường dẫn, package, quyền và thao tác cài theo bài.')

page('4 Đăng ký định nghĩa và cấp phát môi trường')
step(4, 'Đưa gói định nghĩa lên Git và đăng ký', [
    'Đặt topology.yml, provisioning, app và checker đúng cấu trúc gốc repository Sandbox Definition. Đưa phiên bản cần triển khai lên Git và ghi lại revision.',
    'Tạo hoặc cập nhật Sandbox Definition trên Portal CyberRangeCZ bằng Git URL và revision. Chỉ đưa source lên Git chưa tạo bản ghi định nghĩa trên nền tảng.',
], 'Sandbox Definition trỏ đúng repository và phiên bản.', 'Dùng lại quy trình đăng ký; cấu hình lại URL và revision; cung cấp gói source đúng bài.')
step(5, 'Tạo pool từ định nghĩa', [
    'Tạo pool, chọn Sandbox Definition và kích thước phù hợp. Một sandbox có thể chứa nhiều VM đội nên số sandbox không mặc định bằng số đội.',
    'Pool gắn với revision khi tạo. Thay Git không tự cập nhật các VM đang chạy; cần tạo pool mới nếu triển khai revision mới theo cơ chế nền tảng.',
], 'Pool sẵn sàng cấp phát đúng phiên bản bài.', 'Dùng lại cơ chế pool; cấu hình lại kích thước và định nghĩa; tạo môi trường mới khi cần cách ly.')
step(6, 'Allocate và kiểm tra provisioning', [
    'Allocate sandbox, theo dõi tạo VM, mạng và chạy provisioning. Xác nhận hostname, IP, dịch vụ, dữ liệu, agent và kết nối checker đến đội đều đúng.',
    'Nếu provisioning thất bại, xử lý nguyên nhân hạ tầng hoặc playbook rồi kiểm tra lại trước khi tích hợp chấm.',
], 'Môi trường thật được tạo và dịch vụ hoạt động.', 'Dùng lại trình tự cấp phát; tài nguyên và trạng thái phải phù hợp lượt triển khai.')
step(7, 'Lấy bộ truy cập và tách quyền', [
    'BTC lấy management SSH access đúng sandbox, lưu key và config ở nơi vận hành. Kiểm tra đường dẫn key, gateway và SSH không tương tác để collector gọi agent.',
    'Đội nhận quyền SSH hoặc GUI đúng máy được giao. Không phát management key cho đội; rút bớt tên máy trong SSH config không phải cơ chế phân quyền.',
], 'BTC và đội có đường truy cập với quyền phù hợp.', 'Dùng lại cơ chế SSH; cấu hình lại đường dẫn; cấp bộ truy cập đúng môi trường và danh tính.')

page('5 Cấu hình ForcAD và đồng bộ website')
step(8, 'Kết nối engine với checker trong sandbox', [
    'ForcAD không tự tìm checker trong sandbox. Cần adapter cho từng task, profile đúng bài và collector có cấu hình SSH cùng lệnh gọi agent.',
    'Luồng chấm là ForcAD đến adapter, thư mục RPC JSON, collector, SSH, agent trên VM checker rồi dịch vụ đội. Kết quả được chuyển ngược về engine.',
], 'Engine gọi được checker đúng đội và task.', 'Dùng lại giao vận nếu tương thích; cấu hình lại adapter, profile, timeout và lệnh agent; tạo lớp chuyển đổi nếu checker khác giao thức.')
table(['Điểm cấu hình', 'Nội dung cần hoàn thiện'], [
    ['lab.json', 'Mã bài, đội và IP, task, SSH config, checker_host, agent_command, timeout.'],
    ['Checker adapter', 'common.py và wrapper cho từng task; quyền thực thi và quyền ghi RPC.'],
    ['lab_profile.py', 'Đội, task, prefix checker, định dạng flag, độ dài tick và số tick.'],
    ['Lịch và timeout', 'Thời gian check, hạn flag và hạn thực thi phù hợp quy mô; đối chiếu giá trị còn cố định trong engine.'],
    ['Dashboard', 'Lựa chọn chuẩn bị đúng bài; nạp lại frontend và backend khi thay cấu hình hoặc mã.'],
    ['Collector', 'MEKO_LAB đúng bài, đọc cấu hình mới khi khởi động và gọi đúng VM checker.'],
], [4.2,12.6])
step(9, 'Ghép đội và đồng bộ token', [
    'Chuẩn bị đúng profile, tạo hoặc kiểm tra đội và task trên ForcAD. Kiểm tra tên kỹ thuật và IP; đội đã tồn tại ở cùng IP không mặc nhiên được đổi tên đúng.',
    'Ghép đội website với đội ForcAD rồi đồng bộ token từ website. Chức năng sync không tạo đội hoặc VM thiếu. Giữ riêng token đội, credential nội bộ checker và SSH credential.',
], 'Mỗi đội website khớp một đội ForcAD và token đã đồng bộ.', 'Dùng lại chức năng sync; cấu hình lại ánh xạ; xác định lại danh tính và quyền cho đợt thi.')
p('Giờ hiển thị trên website, khoảng truy cập Training và lịch tick ForcAD hiện không tự đồng bộ. BTC cần phối hợp cấu hình; mở website hoặc Training không tự bắt đầu round.')

page('6 Kiểm thử tích hợp và cấu hình Training')
step(10, 'Kiểm tra các đường kết nối', [
    'Chạy website, ForcAD, collector và sandbox. Kiểm tra website lấy điểm và gửi flag tới engine; engine gọi adapter; collector gọi agent; checker thực hiện check, put và get.',
    'Mở được các giao diện hoặc SSH thông chưa chứng minh chấm đúng. Cần thử flag hợp lệ, sai, trùng và hết hạn theo luật, đối chiếu điểm và thời gian xử lý.',
], 'Luồng chấm và nộp flag hoạt động xuyên suốt.', 'Dùng lại khung kiểm thử; tạo riêng test nghiệp vụ và kết quả nghiệm thu cho phiên bản thực tế.')
step(11, 'Tạo Training và xác minh quyền thí sinh', [
    'Tạo hoặc chọn Training Definition chứa hướng dẫn, tạo Training Instance, đặt khoảng truy cập, gán pool và cấp quyền cùng token vào training cho trainee.',
    'Training Run của một trainee nhận sandbox từ pool. Đây không phải quy tắc mỗi sandbox chỉ được có một tài khoản, và cũng không bắt buộc mọi đội dùng chung một tài khoản Portal.',
    'Với topology nhiều đội chung một sandbox, tạo run riêng cho mỗi đội có thể nhân bản cả topology vào các sandbox riêng. Nếu dùng một tài khoản Portal chung cho sân đấu chung, đó là cách vận hành riêng và không tự phân quyền đội. Phải kiểm tra tài khoản VM hoặc GUI và quyền quản trị đúng máy.',
], 'Thí sinh vào đúng training và chỉ được quản trị máy được giao.', 'Dùng lại cơ chế Training; cấu hình lại thời gian, pool và quyền; cung cấp hướng dẫn và credential riêng.')
table(['Thông tin', 'Chức năng'], [
    ['Tài khoản Portal', 'Xác thực người dùng vào CyberRangeCZ.'],
    ['Token Training', 'Vào đợt training được cấp sau bước xác thực Portal.'],
    ['Token đội website và ForcAD', 'Nhận diện đội khi đăng nhập đội và nộp flag.'],
    ['Credential SSH hoặc GUI', 'Đăng nhập vào môi trường VM theo quyền được cấp.'],
], [6.0,10.8])
p('Sau khi cấp quyền, thử lại từ tài khoản thí sinh thực tế: vào training, truy cập đúng VM, đăng nhập website và nộp flag. Kiểm tra bằng tài khoản BTC không thay được bước này.')

page('7 Mở thi và mức tái sử dụng')
step(12, 'Mở cuộc thi và lưu hồ sơ', [
    'Lưu hồ sơ thi thử, đưa dữ liệu và dịch vụ về trạng thái đầu phù hợp, rồi kiểm tra lại. Reset tick hoặc điểm không tự khôi phục source đã vá hay database ứng dụng.',
    'Đến giờ thi, cấp quyền theo phương án đã chọn, giữ website, Docker, collector và sandbox hoạt động, rồi bắt đầu round trên ForcAD để điều phối tick, sinh flag và chấm.',
    'Khoảng truy cập Training nên bao phủ chuẩn bị và thi. Nếu giữ kín bài đến giờ thi, cần kiểm tra cả thời điểm cấp quyền VM. Kết thúc phải lưu kết quả, log và cấu hình trước khi thu hồi hoặc tái tạo.',
], 'Lượt thi có kết quả và hồ sơ truy vết.', 'Dùng lại điều khiển và lưu hồ sơ; chỉnh thủ tục reset theo bài; tạo riêng trạng thái đầu sạch cho lượt mới.')
table(['Thành phần', 'Phần giữ lại', 'Phần phải chuẩn bị lại'], [
    ['Website và engine', 'Code và cơ chế chung.', 'Cấu hình nơi chạy và thông tin cuộc thi.'],
    ['Topology và Ansible', 'Khung khai báo và cài đặt.', 'Đội, IP, mạng, package, path, quyền và dịch vụ.'],
    ['Adapter và collector', 'Giao vận tương thích.', 'Task, profile, lệnh agent và kết nối SSH.'],
    ['Nội dung bài', 'Có thể dùng lại cùng phiên bản đã nghiệm thu.', 'Kịch bản, lỗ hổng, dữ liệu và logic checker của đề khác.'],
    ['Tài khoản và dữ liệu', 'Cơ chế xác thực và lưu trữ.', 'Danh sách đội, quyền, dữ liệu sạch và hồ sơ nghiệm thu.'],
], [3.6,5.8,7.4])
h('Giới hạn của source hiện tại', 2)
p('round1 và meko_boutique có lab config, adapter và profile ForcAD. fashion_shop và fashion_shop_v2 có gói lab riêng nhưng chưa có cùng cấu hình tích hợp engine. Đổi tên thư mục hoặc đặt MEKO_LAB chưa đủ nối chúng với ForcAD.')
p('Một số thông tin còn khai ở nhiều file; dashboard thêm bài cần chỉnh mã; playbook còn giả định tên đội và đường dẫn. Mức tái sử dụng hiện là nền tảng, khung và giao thức, chưa phải tự động sinh và triển khai mọi đề.')

page('8 Phụ lục cài nền tảng và bật lại dự án')
p('Các lệnh dưới đây dùng PowerShell và chạy theo thứ tự trong đúng thư mục. Thay đường dẫn gốc nếu mã nguồn được lưu nơi khác. Cài nền tảng một lần; các lần mở lại dùng phần khởi động bên dưới.')
h('Cài website lần đầu', 2)
code(["$duAn = 'C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform'", 'Set-Location "$duAn/platform/MekoDataCTF_Website"', 'npm install', 'if (!(Test-Path .env)) { Copy-Item .env.example .env }'])
p('Sửa .env với SESSION_SECRET, tài khoản BTC, cổng và FORCAD_URL. Sau đó chạy npm run seed và npm start. Không ghi đè .env đã có hoặc seed lại mỗi lần bật máy.')
h('Cài ForcAD lần đầu', 2)
code(['Set-Location "$duAn/platform/ForcAD-demo"', 'py -3.11 -m pip install -r cli/requirements.txt', 'if (!(Test-Path config.yml)) { Copy-Item config.yml.example config.yml }'])
p('Hoàn thiện config.yml; chỉ khi chưa thiết lập mới chạy py -3.11 control.py setup. Không sinh lại mật khẩu storage trên bản đang có dữ liệu. Dựng frontend trước nếu chưa có front/dist.')
code(['Set-Location "$duAn/platform/ForcAD-demo/front"', 'npm install', 'npm run build', 'Set-Location ..', 'docker compose up -d --build', 'docker compose ps -a'])
p('Đợi database và initializer sẵn sàng rồi chạy docker compose exec -T ticker python /app/scripts/setup_round1.py. Website mặc định ở localhost:3000, dashboard ở 127.0.0.1:18080. Tài khoản hai hệ thống là hai tài khoản riêng.')
h('Bật lại bài đã được cài', 2)
table(['Thành phần', 'Thao tác'], [
    ['Sandbox', 'Xác nhận môi trường và dịch vụ đang hoạt động.'],
    ['ForcAD', 'Trong thư mục ForcAD chạy docker compose up -d.'],
    ['Website', 'Trong terminal riêng tại thư mục website chạy npm start.'],
    ['Collector', 'Tại gốc dự án đặt $env:MEKO_LAB đúng bài rồi chạy py -3.11 platform/ForcAD-demo/collect_checker.py.'],
    ['Cuộc thi', 'Xem trạng thái cũ trên dashboard trước khi tiếp tục hoặc chuẩn bị lượt mới.'],
], [3.2,13.6])
p('Dừng bình thường: dừng round trên dashboard, đợi xử lý hoàn tất, Ctrl+C website và collector, rồi docker compose stop. Không dùng reset database hoặc recycle làm lệnh khởi động thông thường.')

page('9 Phụ lục thư mục và tài liệu tham chiếu')
p('Nền tảng dùng chung được giữ trong platform và shared. Mỗi bài có gói nội dung và cấu hình riêng trong labs. Bộ truy cập nằm trong ops theo môi trường.')
code(['atk_def_platform/', '  platform/', '    MekoDataCTF_Website/       Website va dong bo doi', '    ForcAD-demo/              Engine, profile va adapter', '      collect_checker.py     Cau noi SSH', '      checkers/<ma-bai>/      Wrapper task va RPC', '  shared/labconfig.py        Doc cau hinh lab', '  labs/<ma-bai>/', '    lab.json                 Doi, IP, task, SSH va agent', '    sandbox/', '      topology.yml           May va mang', '      provisioning/          Playbook va template', '      app/                   Ung dung cua bai', '      checker/               Logic checker cua bai', '  ops/<moi-truong>/          SSH key va config dung moi truong', '  report/                    Tai lieu Word va PowerPoint'])
h('Nguồn dự án', 2)
p('Căn cứ chính: README.md; website models/Team.js, scripts/export-lab-teams.js và services/forcadSync.js; ForcAD docker-compose.yml, collect_checker.py, backend/lib/storage/lab_profile.py và competition.py; topology và provisioning của các lab.')
p('Bản hướng dẫn thao tác: docs/QUY-TRINH-TAO-DE-THI-TAI-SU-DUNG.md. Bản phân tích đầy đủ: docs/QUY-TRINH-CAI-DAT-TONG-QUAT-BAO-CAO.md.')
h('Tài liệu chính thức CyberRangeCZ', 2)
for label, url in [
    ('Workflow', 'https://docs.platform.cyberrange.cz/basic-concepts/typical-training-workflow/training-workflow-cloud/'),
    ('Pool', 'https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/pool/'),
    ('Sandbox Access', 'https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/'),
    ('Training Instance', 'https://docs.platform.cyberrange.cz/user-guide-basic/training-agenda/training-instance/'),
    ('Training overview', 'https://docs.platform.cyberrange.cz/user-guide-advanced/trainings/trainings-overview/'),
]:
    para = p(label + '\n' + url)
    for r in para.runs: r.font.size = Pt(9.5)

doc.save(TARGET)
print(TARGET)
