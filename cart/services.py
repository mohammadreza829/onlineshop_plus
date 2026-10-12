from dataclasses import dataclass, field


@dataclass
class CartResult:

    success: bool

    message: str = ""

    data: dict = field(
        default_factory=dict
    )