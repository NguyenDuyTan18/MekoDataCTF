from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_gui_starts_before_shop_health_can_block_it():
    play = yaml.safe_load((ROOT / 'provisioning/playbook.yml').read_text())[0]
    assert any(task.get('ansible.builtin.include_tasks') == 'desktop.yml' for task in play.get('pre_tasks', []))


def test_gui_can_be_repaired_without_web_or_apache():
    path = ROOT / 'provisioning/gui-repair.yml'
    assert path.is_file()
    play = yaml.safe_load(path.read_text())[0]
    assert [t.get('ansible.builtin.include_tasks') for t in play['tasks']] == ['trainee-access.yml', 'desktop.yml']
    desktop = yaml.safe_load((ROOT / 'provisioning/desktop.yml').read_text())
    assert not any('ansible.builtin.uri' in task for task in desktop)
