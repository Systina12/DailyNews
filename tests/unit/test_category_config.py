from preprocessing.classify import Classify
from workflows.news_pipeline import DEFAULT_CATEGORIES


def _make_item(title, summary="", source="Reuters", categories=None):
    return {
        "title": title,
        "summaryText": summary,
        "origin": {"title": source},
        "categories": categories or [],
    }


def test_default_categories_match_requested_sections():
    assert DEFAULT_CATEGORIES == ["头条", "国际财经", "中国财经", "科技", "战争", "国际"]


def test_classify_war_category():
    classifier = Classify(category="战争")
    category, confidence = classifier._classify_item(
        _make_item(
            "Missile attack hits military base",
            "Army units launched an airstrike after days of conflict.",
            source="Defense News",
        )
    )

    assert category == "战争"
    assert confidence >= 0.75


def test_classify_china_finance_category():
    classifier = Classify(category="中国财经")
    category, confidence = classifier._classify_item(
        _make_item(
            "China stocks rise after PBOC support",
            "Shanghai and Shenzhen markets climbed as the central bank signaled fresh liquidity.",
            source="Financial Times",
        )
    )

    assert category == "中国财经"
    assert confidence >= 0.75


def test_classify_global_finance_category():
    classifier = Classify(category="国际财经")
    category, confidence = classifier._classify_item(
        _make_item(
            "US inflation cools as bond yields fall",
            "Markets rallied after lower-than-expected CPI data.",
            source="Bloomberg Markets",
        )
    )

    assert category == "国际财经"
    assert confidence >= 0.75


def test_classify_tech_category():
    classifier = Classify(category="科技")
    category, confidence = classifier._classify_item(
        _make_item(
            "AI chip startup unveils new semiconductor platform",
            "The company said its new software stack improves inference efficiency.",
            source="TechCrunch",
        )
    )

    assert category == "科技"
    assert confidence >= 0.75


def test_classify_politics_falls_back_to_international():
    classifier = Classify(category="国际")
    category, confidence = classifier._classify_item(
        _make_item(
            "Parliament backs new sanctions package",
            "Government leaders said the diplomatic push will continue next week.",
            source="Reuters Politics",
        )
    )

    assert category == "国际"
    assert confidence <= 0.6
