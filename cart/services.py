from dataclasses import dataclass, field


@dataclass
class CartResult:
    success: bool

    message: str = ""

    data: dict = field(default_factory=dict)


MAX_QUANTITY_PER_REQUEST = 100


def parse_quantity(raw, default=1):
    try:
        value = int(raw if raw not in (None, "") else default)
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= MAX_QUANTITY_PER_REQUEST else None
