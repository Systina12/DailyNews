from workflows.news_pipeline import _select_items_for_category


def _make_item(*categories):
    return {"categories": list(categories)}


def test_china_finance_only_uses_china_label():
    raw_items = [
        _make_item("user/-/label/中国"),
        _make_item("user/-/label/亚洲"),
        _make_item("user/-/label/中国", "user/-/label/亚洲"),
    ]

    selected = _select_items_for_category(raw_items, "中国财经")

    assert selected == [raw_items[0], raw_items[2]]


def test_global_finance_excludes_china_label():
    raw_items = [
        _make_item("user/-/label/中国"),
        _make_item("user/-/label/美洲"),
        _make_item("user/-/label/欧洲"),
        _make_item("user/-/label/中国", "user/-/label/欧洲"),
    ]

    selected = _select_items_for_category(raw_items, "国际财经")

    assert selected == [raw_items[1], raw_items[2]]


def test_other_categories_keep_full_candidate_pool():
    raw_items = [
        _make_item("user/-/label/中国"),
        _make_item("user/-/label/欧洲"),
    ]

    selected = _select_items_for_category(raw_items, "战争")

    assert selected == raw_items
