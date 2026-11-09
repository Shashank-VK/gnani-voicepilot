"""Safe calculator and synthetic Kirana catalog tools."""

import ast
import math
import operator
import re
from typing import Any


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""


class SafeCalculator:
    """AST-based safe mathematical expression evaluator (no eval or arbitrary execution)."""

    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sqrt": math.sqrt,
        "ceil": math.ceil,
        "floor": math.floor,
    }

    @classmethod
    def evaluate(cls, expression: str) -> int | float:
        """Safely evaluate an arithmetic expression string."""
        clean_expr = expression.strip().replace("$", "").replace("₹", "").replace(",", "")
        try:
            node = ast.parse(clean_expr, mode="eval")
        except SyntaxError as exc:
            raise ToolExecutionError(f"Invalid mathematical syntax: '{expression}'") from exc

        return cls._eval_node(node.body)

    @classmethod
    def _eval_node(cls, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ToolExecutionError(f"Non-numeric constant not allowed: {node.value}")

        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op_type = type(node.op)
            if op_type in cls.ALLOWED_OPERATORS:
                if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                    raise ToolExecutionError("Division by zero is undefined")
                return cls.ALLOWED_OPERATORS[op_type](left, right)
            raise ToolExecutionError(f"Unsupported binary operator: {op_type.__name__}")

        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in cls.ALLOWED_OPERATORS:
                return cls.ALLOWED_OPERATORS[op_type](operand)
            raise ToolExecutionError(f"Unsupported unary operator: {op_type.__name__}")

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in cls.ALLOWED_FUNCTIONS:
                func = cls.ALLOWED_FUNCTIONS[node.func.id]
                args = [cls._eval_node(arg) for arg in node.args]
                return func(*args)
            raise ToolExecutionError(f"Unsupported function call: {getattr(node.func, 'id', 'unknown')}")

        raise ToolExecutionError(f"Unsupported expression node: {type(node).__name__}")


class CatalogItem(dict):
    """Catalog item dictionary with string comparison support."""

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            other_lower = other.lower()
            return (
                self.get("name", "").lower() == other_lower
                or self.get("matched", "").lower() == other_lower
                or other_lower in [a.lower() for a in self.get("aliases", [])]
            )
        return super().__eq__(other)

    def __str__(self) -> str:
        return self.get("matched") or self.get("name", "")


class KiranaCatalog:
    """Synthetic inventory catalog for neighbourhood kirana store."""

    ITEMS = [
        {
            "name": "atta",
            "aliases": ["atta", "wheat flour", "flour", "gehu ka atta", "gehu"],
            "unit": "kilo",
            "price": 55,
            "stock": 25,
        },
        {
            "name": "chawal",
            "aliases": ["chawal", "rice"],
            "unit": "kilo",
            "price": 65,
            "stock": 30,
        },
        {
            "name": "toor daal",
            "aliases": ["toor daal", "toor dal", "daal", "dal", "arhar daal", "arhar dal"],
            "unit": "kilo",
            "price": 170,
            "stock": 12,
        },
        {
            "name": "sarso tel",
            "aliases": ["sarso tel", "mustard oil", "tel", "oil", "sarson tel"],
            "unit": "litre",
            "price": 145,
            "stock": 18,
        },
        {
            "name": "chini",
            "aliases": ["chini", "sugar", "shakkar"],
            "unit": "kilo",
            "price": 45,
            "stock": 20,
        },
        {
            "name": "namak",
            "aliases": ["namak", "salt"],
            "unit": "packet",
            "price": 28,
            "stock": 40,
        },
        {
            "name": "sabun",
            "aliases": ["sabun", "soap"],
            "unit": "piece",
            "price": 35,
            "stock": 60,
        },
        {
            "name": "doodh",
            "aliases": ["doodh", "milk"],
            "unit": "litre",
            "price": 56,
            "stock": 10,
        },
        {
            "name": "anda",
            "aliases": ["anda", "ande", "egg", "eggs"],
            "unit": "piece",
            "price": 7,
            "stock": 120,
        },
        {
            "name": "biscuit",
            "aliases": ["biscuit", "biscuits"],
            "unit": "packet",
            "price": 25,
            "stock": 50,
        },
        {
            "name": "chai patti",
            "aliases": ["chai patti", "chai", "tea", "tea powder"],
            "unit": "packet",
            "price": 140,
            "stock": 22,
        },
        {
            "name": "masala",
            "aliases": ["masala", "garam masala"],
            "unit": "packet",
            "price": 60,
            "stock": 30,
        },
        {
            "name": "besan",
            "aliases": ["besan", "gram flour"],
            "unit": "kilo",
            "price": 70,
            "stock": 15,
        },
        {
            "name": "poha",
            "aliases": ["poha", "chivda"],
            "unit": "kilo",
            "price": 48,
            "stock": 18,
        },
    ]

    UNIT_NORMALIZATION = {
        "kilo": "kilo",
        "kilos": "kilo",
        "kg": "kilo",
        "kgs": "kilo",
        "litre": "litre",
        "litres": "litre",
        "liter": "litre",
        "liters": "litre",
        "l": "litre",
        "packet": "packet",
        "packets": "packet",
        "pkt": "packet",
        "pkts": "packet",
        "piece": "piece",
        "pieces": "piece",
        "pc": "piece",
        "pcs": "piece",
    }

    @classmethod
    def _make_item(cls, raw: dict[str, Any], matched: str | None = None) -> CatalogItem:
        d = dict(raw)
        if matched:
            d["matched"] = matched
        return CatalogItem(d)

    @classmethod
    def find_item(cls, name: str) -> dict[str, Any] | None:
        """Find catalog item by name or alias, case-insensitive."""
        if not name or not isinstance(name, str):
            return None
        clean = name.strip().lower()
        for item in cls.ITEMS:
            if clean == item["name"].lower() or clean in [a.lower() for a in item["aliases"]]:
                return cls._make_item(item, matched=clean)
        clean_no_punct = re.sub(r"[^\w\s]", "", clean).strip()
        for item in cls.ITEMS:
            if clean_no_punct == item["name"].lower() or clean_no_punct in [a.lower() for a in item["aliases"]]:
                return cls._make_item(item, matched=clean_no_punct)
        return None

    @classmethod
    def find_in_text(cls, text: str) -> CatalogItem | None:
        """Find first matching catalog item in a free-form sentence."""
        if not text:
            return None
        candidates: list[tuple[str, dict[str, Any]]] = []
        for item in cls.ITEMS:
            for alias in [item["name"]] + item["aliases"]:
                candidates.append((alias.lower(), item))
        candidates.sort(key=lambda x: len(x[0]), reverse=True)

        for alias, item in candidates:
            if re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE):
                return cls._make_item(item, matched=alias)
        return None

    @classmethod
    def lookup(cls, query: str) -> str:
        """Return Hinglish line with price and stock availability."""
        item = cls.find_in_text(query)
        if not item:
            item = cls.find_item(query)

        if not item:
            return (
                "Maaf kijiye, yeh item hamare catalog mein nahi mila. "
                "Aap atta, chawal, daal, tel, doodh pooch sakte hain."
            )

        name_display = item.get("matched", item["name"]).capitalize()
        parsed = cls.parse_order(query)
        subtotal_phrase = ""
        for qty, unit, p_item in parsed:
            if p_item["name"] == item["name"]:
                subtotal = SafeCalculator.evaluate(f"{qty} * {item['price']}")
                subtotal_val = (
                    int(subtotal)
                    if isinstance(subtotal, (int, float)) and subtotal == int(subtotal)
                    else subtotal
                )
                subtotal_phrase = f" ({qty} {unit} ka ₹{subtotal_val})"
                break

        price_part = f"{name_display} — ₹{item['price']} per {item['unit']}{subtotal_phrase}"
        if item["stock"] > 0:
            stock_part = f"stock mein hai ({item['stock']} {item['unit']} available hai)."
        else:
            stock_part = "abhi out of stock hai."

        return f"{price_part}, {stock_part}"

    @classmethod
    def parse_order(cls, text: str) -> list[tuple[int, str, CatalogItem]]:
        """Extract list of (qty, unit, item) from text."""
        if not text:
            return []

        alias_to_item: dict[str, dict[str, Any]] = {}
        for item in cls.ITEMS:
            for alias in [item["name"]] + item["aliases"]:
                al = alias.lower()
                if al not in alias_to_item:
                    alias_to_item[al] = item

        sorted_aliases = sorted(alias_to_item.keys(), key=len, reverse=True)
        item_regex = "|".join(re.escape(a) for a in sorted_aliases)
        unit_regex = r"(?:kilo[s]?|kg[s]?|litre[s]?|liter[s]?|\bl\b|packet[s]?|pkt[s]?|piece[s]?|pc[s]?)"

        pattern = re.compile(
            rf"\b(?P<qty>\d+)\s*(?:(?P<unit>{unit_regex})\s+)?(?:ka\s+|ki\s+|ke\s+)?(?P<item>{item_regex})\b",
            re.IGNORECASE,
        )

        results: list[tuple[int, str, CatalogItem]] = []
        for match in pattern.finditer(text):
            qty = int(match.group("qty"))
            matched_alias = match.group("item").lower()
            raw_item = alias_to_item[matched_alias]
            matched_unit = match.group("unit")

            if matched_unit:
                unit = cls.UNIT_NORMALIZATION.get(matched_unit.lower(), raw_item["unit"])
            else:
                unit = raw_item["unit"]

            catalog_item = cls._make_item(raw_item, matched=matched_alias)
            results.append((qty, unit, catalog_item))

        return results

    @classmethod
    def order_total(cls, lines: list[tuple[Any, str, Any]]) -> float:
        """Compute order total using SafeCalculator expression evaluation."""
        if not lines:
            return 0.0

        terms: list[str] = []
        for qty, _unit, item in lines:
            if isinstance(item, dict):
                price = item.get("price", 0)
            else:
                found = cls.find_item(str(item))
                price = found.get("price", 0) if found else 0
            terms.append(f"({qty} * {price})")

        expr = " + ".join(terms)
        result = SafeCalculator.evaluate(expr)
        return float(result)
