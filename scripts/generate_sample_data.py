from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)

ROOT = Path(__file__).resolve().parents[1] / "sample_data"
ROOT.mkdir(exist_ok=True)

REGIONS = ["North", "South", "East", "West"]
PRODUCTS = [
    ("Aurora Headphones", "Audio", 89),
    ("Nimbus Laptop", "Computers", 1199),
    ("Pulse Keyboard", "Accessories", 79),
    ("Halo Monitor", "Computers", 329),
    ("Drift Mouse", "Accessories", 49),
    ("Canyon Webcam", "Accessories", 59),
    ("Lumen Desk Lamp", "Home", 39),
    ("Forge Standing Desk", "Home", 449),
]
CUSTOMERS = [
    ("Brightline Retail", "Enterprise", "UK"),
    ("Harbor Clinic", "Healthcare", "UK"),
    ("Northwind Schools", "Education", "UK"),
    ("Summit Foods", "SMB", "IE"),
    ("Cedar Logistics", "Enterprise", "UK"),
    ("Pixel Cafe Group", "SMB", "UK"),
    ("Atlas Motors", "Enterprise", "DE"),
    ("Quiet Library Trust", "Education", "UK"),
    ("Orbital Labs", "SMB", "NL"),
    ("Greenfield Co-op", "SMB", "UK"),
]

start = date(2024, 1, 1)
sales_path = ROOT / "sales.csv"
with sales_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(
        [
            "order_id",
            "order_date",
            "region",
            "product",
            "category",
            "customer",
            "quantity",
            "unit_price",
            "revenue",
            "cost",
        ]
    )
    order_id = 1000
    for day in range(365):
        current = start + timedelta(days=day)
        n_orders = random.randint(4, 12)
        for _ in range(n_orders):
            product, category, price = random.choice(PRODUCTS)
            qty = random.randint(1, 8)
            # West over-indexes; Halo Monitor is weak; one injected anomaly
            region = random.choices(REGIONS, weights=[18, 16, 22, 30])[0]
            if product == "Halo Monitor":
                qty = random.choice([1, 1, 1, 2])
            revenue = qty * price
            if order_id == 1420:
                revenue = 25000
            cost = round(revenue * random.uniform(0.45, 0.72), 2)
            customer = random.choice(CUSTOMERS)[0]
            writer.writerow(
                [
                    f"ORD-{order_id}",
                    current.isoformat(),
                    region,
                    product,
                    category,
                    customer,
                    qty,
                    price,
                    revenue,
                    cost,
                ]
            )
            order_id += 1

customers_path = ROOT / "customers.csv"
with customers_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["customer", "segment", "country", "signup_date", "account_manager"])
    for i, (name, segment, country) in enumerate(CUSTOMERS):
        writer.writerow(
            [
                name,
                segment,
                country,
                (date(2022, 1, 1) + timedelta(days=40 * i)).isoformat(),
                random.choice(["Amelia", "Jonah", "Priya", "Chris"]),
            ]
        )

print(f"Wrote {sales_path} and {customers_path}")
