"""Analytics helpers: margins and review sentiment scoring."""


def gross_margin_pct(revenue: float, cogs: float) -> float:
    if revenue == 0:
        return 0.0
    return round((revenue - cogs) / revenue * 100, 1)


def average_rating(ratings: list[int]) -> float:
    return round(sum(ratings) / len(ratings), 2) if ratings else 0.0
