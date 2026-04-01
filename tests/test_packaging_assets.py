from importlib import resources


def test_package_assets_exist():
    base = resources.files("tokenwaster")
    assert base.joinpath("assets", "pic1.png").is_file()
    assert base.joinpath("assets", "pic2.png").is_file()
    assert base.joinpath("assets", "pic3_en.png").is_file()
