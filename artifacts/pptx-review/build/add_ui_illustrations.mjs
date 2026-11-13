import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

const root = 'C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform';
const runtime = 'C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES = runtime + '/node/node_modules';
const { PresentationFile, FileBlob } = await import(
  pathToFileURL(runtime + '/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href
);
const skill = 'C:/Users/Admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1110.11613/skills/presentations';
const { finalizePresentation } = await import(pathToFileURL(skill + '/container_tools/artifact_tool_utils.mjs').href);
const pythonExecutable = 'C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';

const sourcePath = path.join(root, 'report/Quy_trinh_trien_khai_MekoDataCTF_CTU_Chi_tiet.pptx');
const outputPath = path.join(root, 'report/Quy_trinh_trien_khai_MekoDataCTF_CTU_Chi_tiet_minh_hoa.pptx');
const buildPath = path.join(root, 'artifacts/pptx-review/build');
const deck = await PresentationFile.importPptx(await FileBlob.load(sourcePath));

const illustrations = [
  { slide: 4, image: 'artifacts/admin-dashboard.png', caption: 'Giao diện quản trị website', alt: 'Ảnh chụp giao diện quản trị MekoDataCTF', crop: { left: 0, top: 0, right: 0, bottom: 0.4 }, source: 'artifacts/admin-dashboard.png' },
  { slide: 5, image: 'artifacts/forcad-ui/07-admin.png', caption: 'Giao diện bảng điều khiển ForcAD', alt: 'Ảnh chụp giao diện bảng điều khiển ForcAD', source: 'artifacts/forcad-ui/07-admin.png' },
  { slide: 15, image: 'artifacts/forcad-ui/12-checker-log.png', caption: 'Giao diện nhật ký checker', alt: 'Ảnh chụp giao diện nhật ký checker', source: 'artifacts/forcad-ui/12-checker-log.png' },
  { slide: 16, image: 'artifacts/forcad-ui/08-create-team.png', caption: 'Giao diện quản lý đội', alt: 'Ảnh chụp giao diện tạo đội', source: 'artifacts/forcad-ui/08-create-team.png' },
  { slide: 17, image: 'artifacts/forcad-ui/05-submit.png', caption: 'Giao diện nộp flag', alt: 'Ảnh chụp giao diện nộp flag', source: 'artifacts/forcad-ui/05-submit.png' },
  { slide: 19, image: 'artifacts/forcad-ui/06-round-control.png', caption: 'Giao diện điều khiển round', alt: 'Ảnh chụp giao diện điều khiển round', source: 'artifacts/forcad-ui/06-round-control.png' },
  { slide: 20, image: 'artifacts/forcad-ui/02-live.png', caption: 'Giao diện theo dõi cuộc thi trực tiếp', alt: 'Ảnh chụp giao diện thi trực tiếp', source: 'artifacts/forcad-ui/02-live.png' },
];

function addCaption(slide, label) {
  const shape = slide.shapes.add({
    geometry: 'textbox',
    name: 'ui-illustration-caption',
    position: { left: 750, top: 482, width: 455, height: 34 },
    fill: 'none',
    line: { fill: 'none', width: 0 },
  });
  shape.text = label;
  shape.text.style = {
    typeface: 'Times New Roman', fontSize: 20, color: '#0070C0', bold: true,
    alignment: 'center', verticalAlignment: 'middle', wrap: 'square', autoFit: 'none', insets: 0,
  };
}

for (const item of illustrations) {
  const slide = deck.slides.items[item.slide - 1];
  for (const shape of slide.shapes.items) {
    if (String(shape.name).startsWith('action-')) {
      shape.position = { ...shape.position, width: 630 };
      shape.text.style = {
        typeface: 'Times New Roman', fontSize: 22, color: '#173E53',
        alignment: 'left', verticalAlignment: 'top', wrap: 'square', autoFit: 'none', insets: 0,
      };
    } else if (shape.name === 'completion') {
      shape.position = { ...shape.position, width: 650 };
      shape.text.style = {
        typeface: 'Times New Roman', fontSize: 22, color: '#173E53',
        alignment: 'left', verticalAlignment: 'top', wrap: 'square', autoFit: 'none', insets: 0,
      };
    }
  }

  slide.shapes.add({
    geometry: 'rect', name: 'ui-illustration-frame',
    position: { left: 735, top: 210, width: 480, height: 305 },
    fill: '#FFFFFF', line: { fill: '#D4E2EC', width: 1.2 },
  });
  const imageBytes = new Uint8Array(await fs.readFile(path.join(root, item.image)));
  slide.images.add({
    blob: imageBytes,
    contentType: 'image/png',
    alt: item.alt,
    fit: 'contain',
    ...(item.crop ? { crop: item.crop } : {}),
    position: { left: 745, top: 220, width: 460, height: 250 },
  });
  addCaption(slide, item.caption);
  slide.speakerNotes.text = `${slide.speakerNotes.text || ''}\n\nMinh họa giao diện: ${item.source}.`;
}

await fs.mkdir(buildPath + '/ui-render', { recursive: true });
for (const item of illustrations) {
  const slide = deck.slides.items[item.slide - 1];
  const png = await deck.export({ slide, format: 'png', scale: 1 });
  await fs.writeFile(path.join(buildPath, `ui-render/slide-${item.slide}.png`), new Uint8Array(await png.arrayBuffer()));
}

const candidatePath = path.join(buildPath, 'candidate-ui.pptx');
await (await PresentationFile.exportPptx(deck)).save(candidatePath);
const sourceHash = createHash('sha256').update(await fs.readFile(sourcePath)).digest('hex');
const finalized = await finalizePresentation({
  workspaceDir: root,
  candidatePath,
  finalPath: outputPath,
  explicitTotalSlideCount: 25,
  requiredNativeTableOwnerSlides: [23],
  requiredNativeChartOwnerSlides: [],
  pythonExecutable,
  integrityValidatorPath: path.join(skill, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skill, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit', '--require-native-table-slide', '23'],
  fontPolicy: { basis: 'reference', families: ['Times New Roman', 'Calibri', 'Readex Pro'], referencePath: sourcePath, referenceSha256: sourceHash },
  verifyArtifactToolImport: true,
  receiptPath: path.join(buildPath, 'validation-ui.json'),
});
console.log(JSON.stringify({ candidatePath, outputPath, slides: illustrations.map(x => x.slide), totalSlides: deck.slides.items.length, finalized }));
