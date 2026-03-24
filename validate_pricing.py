#!/usr/bin/env python3
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data.json"


def load_data():
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def to_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def format_money(value):
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized}"


def find_record(records, deployment, license_name, seats):
    for rec in records:
        seat_range = rec["seat_range"]
        if rec["deployment"] != deployment or rec["license"] != license_name or not seat_range:
            continue
        if seat_range["min"] <= seats and (seat_range["max"] is None or seats <= seat_range["max"]):
            return rec
    return None


def find_step_base(records, deployment, license_name, seats, edition):
    candidates = []
    for rec in records:
        if rec["deployment"] != deployment or rec["license"] != license_name or rec["seats"] > seats:
            continue
        list_price = rec["editions"][edition]["list_price"]
        if list_price is not None:
            candidates.append(rec)
    if not candidates:
        return None
    return max(candidates, key=lambda rec: rec["seats"])


def compute_standard_product(data, product, deployment, license_name, edition, seats):
    records = data["products"][product]["records"]
    record = find_record(records, deployment, license_name, seats)
    if not record:
        return {
            "ok": False,
            "status": "CONTACT" if seats >= 10000 else "MISSING_RANGE",
            "list_price": None,
            "unit_price": None,
            "range_text": "-",
        }

    info = record["editions"][edition]
    range_text = (
        f"{record['seat_range']['min']} - {record['seat_range']['max']}"
        if record["seat_range"] and record["seat_range"]["max"] is not None
        else f"{record['seat_range']['min']}+"
        if record["seat_range"]
        else "-"
    )
    if info["list_price"] is None and info["unit_price"] is None:
        return {
            "ok": False,
            "status": "CONTACT",
            "list_price": None,
            "unit_price": None,
            "range_text": range_text,
        }

    unit_price = to_decimal(info["unit_price"])
    if product == "ONES Desk" and unit_price is not None:
        list_price = unit_price * Decimal(seats)
    else:
        step_base = find_step_base(records, deployment, license_name, seats, edition)
        step_seats = step_base["seats"] if step_base else None
        step_price = to_decimal(step_base["editions"][edition]["list_price"]) if step_base else None
        delta = seats - step_seats if step_seats is not None else 0
        if step_seats is not None and step_price is not None and unit_price is not None:
            list_price = step_price + Decimal(delta) * unit_price
        elif step_seats is not None and step_price is not None and delta == 0:
            list_price = step_price
        elif unit_price is not None:
            list_price = unit_price * Decimal(seats)
        else:
            list_price = to_decimal(info["list_price"])

    return {
        "ok": True,
        "status": "OK",
        "list_price": list_price,
        "unit_price": unit_price,
        "range_text": range_text,
    }


def compute_case(data, case):
    raw_total = Decimal("0")
    product_rows = {}

    for product, seats in case["products"]:
        if product == "ONES Copilot":
            project = product_rows.get("ONES Project 项目管理平台")
            if not project or not project["ok"]:
                product_rows[product] = {
                    "ok": False,
                    "status": "MISSING_PROJECT",
                    "list_price": None,
                    "unit_price": None,
                    "range_text": "-",
                }
                continue
            project_list = project["list_price"]
            project_unit = project["unit_price"]
            product_rows[product] = {
                "ok": True,
                "status": "OK",
                "list_price": project_list * Decimal("0.35"),
                "unit_price": project_unit * Decimal("0.35") if project_unit is not None else None,
                "range_text": project["range_text"],
            }
        else:
            product_rows[product] = compute_standard_product(
                data,
                product,
                case["deployment"],
                case["license"],
                case["edition"],
                seats,
            )

        row = product_rows[product]
        if row["ok"] and row["list_price"] is not None:
            raw_total += row["list_price"]

    discount_rate = Decimal(str(case["discount"])) / Decimal("100")
    service_discount_rate = Decimal(str(case["service_discount"])) / Decimal("100")
    discounted_software_total = raw_total * discount_rate
    service_total = Decimal(str(case["service_days"])) * Decimal(str(case["service_rate"])) * service_discount_rate
    total = discounted_software_total + service_total

    software_tax_rate = Decimal("0.13") if case["license"] == "一次性授权版" else Decimal("0.06")
    service_tax_rate = Decimal("0.06")
    software_net_total = discounted_software_total / (Decimal("1") + software_tax_rate) if discounted_software_total else Decimal("0")
    service_net_total = service_total / (Decimal("1") + service_tax_rate) if service_total else Decimal("0")
    low_min_threshold = False
    if case["deployment"] == "私有部署":
        threshold = Decimal(str(
            data["notes"]["private_min_perpetual"]
            if case["license"] == "一次性授权版"
            else data["notes"]["private_min_subscription"]
        ))
        low_min_threshold = discounted_software_total > 0 and discounted_software_total < threshold

    return {
        "raw_total": raw_total,
        "discounted_software_total": discounted_software_total,
        "service_total": service_total,
        "total": total,
        "software_net_total": software_net_total,
        "service_net_total": service_net_total,
        "low_min_threshold": low_min_threshold,
        "product_rows": product_rows,
    }


def assert_money(name, actual, expected):
    expected_decimal = Decimal(str(expected))
    if actual.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) != expected_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):
        raise AssertionError(f"{name}: expected {format_money(expected_decimal)}, got {format_money(actual)}")


def run_cases():
    data = load_data()
    cases = [
        {
            "name": "project_10_public_annual_standard",
            "input": {
                "deployment": "公有云",
                "license": "按年订阅版",
                "edition": "标准版 V6",
                "discount": 100,
                "service_days": 0,
                "service_rate": 3000,
                "service_discount": 100,
                "products": [("ONES Project 项目管理平台", 10)],
            },
            "expect": {
                "raw_total": "6250",
                "discounted_software_total": "6250",
                "service_total": "0",
                "total": "6250",
                "software_net_total": "5896.23",
            },
        },
        {
            "name": "assistant_is_35_percent_of_project",
            "input": {
                "deployment": "公有云",
                "license": "按年订阅版",
                "edition": "标准版 V6",
                "discount": 100,
                "service_days": 0,
                "service_rate": 3000,
                "service_discount": 100,
                "products": [("ONES Project 项目管理平台", 10), ("ONES Copilot", 10)],
            },
            "expect": {
                "raw_total": "8437.5",
                "discounted_software_total": "8437.5",
                "total": "8437.5",
                "assistant_price": "2187.5",
            },
        },
        {
            "name": "bundle_with_service_and_discount",
            "input": {
                "deployment": "公有云",
                "license": "按年订阅版",
                "edition": "标准版 V6",
                "discount": 80,
                "service_days": 1,
                "service_rate": 3000,
                "service_discount": 70,
                "products": [
                    ("ONES Project 项目管理平台", 50),
                    ("ONES Wiki 知识库管理平台", 50),
                    ("ONES Desk", 50),
                    ("ONES Copilot", 50),
                ],
            },
            "expect": {
                "raw_total": "72687.5",
                "discounted_software_total": "58150",
                "service_total": "2100",
                "total": "60250",
            },
        },
        {
            "name": "private_subscription_below_minimum",
            "input": {
                "deployment": "私有部署",
                "license": "按年订阅版",
                "edition": "企业版 V6",
                "discount": 60,
                "service_days": 2,
                "service_rate": 3000,
                "service_discount": 100,
                "products": [("ONES Project 项目管理平台", 10)],
            },
            "expect": {
                "raw_total": "10000",
                "discounted_software_total": "6000",
                "service_total": "6000",
                "total": "12000",
                "low_min_threshold": True,
            },
        },
        {
            "name": "perpetual_license_uses_13_percent_tax",
            "input": {
                "deployment": "私有部署",
                "license": "一次性授权版",
                "edition": "企业版 V6",
                "discount": 100,
                "service_days": 0,
                "service_rate": 3000,
                "service_discount": 100,
                "products": [("ONES Project 项目管理平台", 50)],
            },
            "expect": {
                "raw_total": "150000",
                "discounted_software_total": "150000",
                "total": "150000",
                "software_net_total": "132743.36",
            },
        },
        {
            "name": "assistant_requires_project",
            "input": {
                "deployment": "公有云",
                "license": "按年订阅版",
                "edition": "企业版 V6",
                "discount": 100,
                "service_days": 0,
                "service_rate": 3000,
                "service_discount": 100,
                "products": [("ONES Copilot", 50)],
            },
            "expect": {
                "assistant_status": "MISSING_PROJECT",
                "raw_total": "0",
                "total": "0",
            },
        },
    ]

    passed = 0
    for case in cases:
        result = compute_case(data, case["input"])
        expect = case["expect"]
        assert_money(case["name"] + ".raw_total", result["raw_total"], expect["raw_total"])
        assert_money(case["name"] + ".discounted_software_total", result["discounted_software_total"], expect.get("discounted_software_total", result["discounted_software_total"]))
        assert_money(case["name"] + ".service_total", result["service_total"], expect.get("service_total", result["service_total"]))
        assert_money(case["name"] + ".total", result["total"], expect["total"])
        if "software_net_total" in expect:
            assert_money(case["name"] + ".software_net_total", result["software_net_total"], expect["software_net_total"])
        if "assistant_price" in expect:
            assert_money(case["name"] + ".assistant_price", result["product_rows"]["ONES Copilot"]["list_price"], expect["assistant_price"])
        if "assistant_status" in expect:
            actual_status = result["product_rows"]["ONES Copilot"]["status"]
            if actual_status != expect["assistant_status"]:
                raise AssertionError(f"{case['name']}.assistant_status: expected {expect['assistant_status']}, got {actual_status}")
        if "low_min_threshold" in expect and result["low_min_threshold"] != expect["low_min_threshold"]:
            raise AssertionError(
                f"{case['name']}.low_min_threshold: expected {expect['low_min_threshold']}, got {result['low_min_threshold']}"
            )
        passed += 1
        print(f"PASS {case['name']}")

    print(f"ALL PASSED ({passed} cases)")


if __name__ == "__main__":
    run_cases()
