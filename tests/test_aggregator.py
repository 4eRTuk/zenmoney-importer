from aggregator import aggregate


def test_returns_list(tmp_path, app_config):
    month_folder = tmp_path / "07_26"
    month_folder.mkdir()
    result = aggregate(month_folder, app_config)
    assert isinstance(result, list)


def test_manual_placeholders_included_when_no_source_files(tmp_path, app_config):
    month_folder = tmp_path / "07_26"
    month_folder.mkdir()
    result = aggregate(month_folder, app_config)
    source_types = [r.source_type for r in result]
    assert "manual_placeholder" in source_types


def test_exactly_5_records_with_only_placeholders(tmp_path, app_config):
    month_folder = tmp_path / "07_26"
    month_folder.mkdir()
    result = aggregate(month_folder, app_config)
    assert len(result) == 5
