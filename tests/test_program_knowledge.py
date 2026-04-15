from packages.core.program_knowledge import (
    get_program_md_path,
    get_program_name,
    list_supported_programs,
    normalize_program_code,
)


def test_program_md_exists():
    path = get_program_md_path()
    assert path.exists()


def test_program_alias_resolution():
    assert normalize_program_code('EEE') == 'ETE'
    assert normalize_program_code('ece') == 'ETE'
    assert normalize_program_code('CSE') == 'CSE'


def test_program_name_resolution():
    assert get_program_name('CSE') == 'Computer Science & Engineering'
    assert get_program_name('EEE') == 'Electronic & Telecom Engineering'


def test_supported_programs_non_empty():
    programs = list_supported_programs()
    assert isinstance(programs, list)
    assert len(programs) > 0
    assert all('code' in p and 'name' in p for p in programs)
