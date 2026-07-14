from discovery import discover_sources


def test_discovers_revolut_invest_file(tmp_path, app_config):
    (tmp_path / "trading-account-statement_2026-07.xlsx").touch()
    result = discover_sources(tmp_path, app_config)
    assert result.revolut_invest is not None
    assert result.revolut_invest.name == "trading-account-statement_2026-07.xlsx"


def test_discovers_tradernet_file(tmp_path, app_config):
    (tmp_path / "tradernet_table.xlsx").touch()
    result = discover_sources(tmp_path, app_config)
    assert result.tradernet is not None
    assert result.tradernet.name == "tradernet_table.xlsx"


def test_returns_none_when_revolut_invest_missing(tmp_path, app_config):
    result = discover_sources(tmp_path, app_config)
    assert result.revolut_invest is None


def test_returns_none_when_tradernet_missing(tmp_path, app_config):
    result = discover_sources(tmp_path, app_config)
    assert result.tradernet is None


def test_multiple_revolut_invest_files_selects_first_alphabetically(tmp_path, app_config):
    (tmp_path / "trading-account-statement_2026-06.xlsx").touch()
    (tmp_path / "trading-account-statement_2026-07.xlsx").touch()
    result = discover_sources(tmp_path, app_config)
    assert result.revolut_invest is not None
    assert result.revolut_invest.name == "trading-account-statement_2026-06.xlsx"
