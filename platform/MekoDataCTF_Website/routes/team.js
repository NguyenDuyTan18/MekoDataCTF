const router = require('express').Router();
const teamController = require('../controllers/teamController');
const { requireCaptain, requireContestant } = require('../middlewares/auth');

// Chưa có đội: trang chọn Tạo đội / Vào đội. Đã có đội: trang thông tin đội.
router.get('/', requireContestant, teamController.show);
router.post('/profile', requireContestant, teamController.saveProfile);
router.post('/create', requireContestant, teamController.create);
router.post('/join', requireContestant, teamController.join);
router.post('/leave', requireContestant, teamController.leave);

// Chỉ đội trưởng
router.get('/edit', requireCaptain, teamController.edit);
router.post('/', requireCaptain, teamController.save);
router.post('/members/:id/remove', requireCaptain, teamController.removeMember);
router.post('/disband', requireCaptain, teamController.disband);

module.exports = router;
