"""
Reproducible synthetic marketing data generator.

Generates realistic, mathematically consistent datasets for:
- Products (>= 100)
- Customers (>= 1000)
- Purchases (>= 5000)

Saves to:
- data/raw/products.csv
- data/raw/customers.csv
- data/raw/purchases.csv

Guarantees:
- Products have realistic popularity distribution (power-law / Zipf)
- Students have meaningful purchasing patterns (budget items, specific categories)
- Repeat customers (VIP / Regular) spend differently from low-frequency customers
- Totals, counts, and revenue are strictly mathematically consistent
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
sys.path.insert(0, str(ROOT))

import pandas as pd
from app.services.validator import validate_all

# Fixed seed
SEED = 42

CATEGORIES: list[str] = [
    "Electronics",
    "Fashion",
    "Home & Living",
    "Books & Media",
    "Sports & Outdoors",
    "Health & Beauty",
]

PRODUCT_TEMPLATES: dict[str, list[tuple[str, float, float]]] = {
    "Electronics": [
        ("Wireless Noise-Canceling Headphones", 149.99, 65.0),
        ("Ultra-Slim Power Bank 20000mAh", 39.99, 16.0),
        ("Mechanical Gaming Keyboard", 89.99, 38.0),
        ("Smart Fitness Watch Pro", 199.99, 85.0),
        ("Bluetooth Portable Speaker", 49.99, 21.0),
        ("Ergonomic Wireless Mouse", 29.99, 11.5),
        ("4K USB-C Multi-Port Hub", 59.99, 24.0),
        ("Active Noise Cancelling Earbuds", 79.99, 32.0),
        ("Dual Monitor Stand Arm", 69.99, 28.0),
        ("Fast Wireless Charging Stand", 24.99, 9.0),
    ],
    "Fashion": [
        ("Classic Organic Cotton T-Shirt", 24.99, 8.5),
        ("Slim-Fit Stretch Denim Jeans", 59.99, 22.0),
        ("Water-Resistant Commuter Backpack", 69.99, 26.0),
        ("Merino Wool Blend Sweater", 89.99, 35.0),
        ("Breathable Athletic Sneakers", 109.99, 42.0),
        ("Polarized Aviator Sunglasses", 44.99, 15.0),
        ("Genuine Leather Minimalist Wallet", 34.99, 12.0),
        ("Thermal Insulated Winter Jacket", 139.99, 55.0),
        ("Everyday Canvas Tote Bag", 19.99, 6.0),
        ("Stainless Steel Casual Watch", 79.99, 28.0),
    ],
    "Home & Living": [
        ("Stainless Steel French Press Coffee Maker", 34.99, 13.0),
        ("Aromatherapy Essential Oil Diffuser", 29.99, 10.5),
        ("Ceramic Non-Stick Frying Pan 10-inch", 44.99, 17.0),
        ("Bamboo Luxury Cutting Board Set", 27.99, 9.5),
        ("Weighted Blanket 15 lbs", 74.99, 29.0),
        ("LED Desk Lamp with Wireless Charging", 39.99, 15.0),
        ("Vacuum Insulated Water Bottle 32oz", 24.99, 8.0),
        ("Memory Foam Ergonomic Seat Cushion", 36.99, 14.0),
        ("Microfiber Queen Bed Sheet Set", 49.99, 18.0),
        ("Smart Wi-Fi LED Light Strip", 22.99, 7.5),
    ],
    "Books & Media": [
        ("Data Structures & Algorithms in Python", 49.99, 18.0),
        ("Designing Data-Intensive Applications", 54.99, 20.0),
        ("The Lean Startup Handbook", 21.99, 7.0),
        ("Atomic Habits for Success", 18.99, 6.0),
        ("Machine Learning Engineering Guide", 59.99, 22.0),
        ("Creative Strategy in Modern Marketing", 32.99, 11.0),
        ("Deep Learning: Foundations and Practice", 64.99, 24.0),
        ("Zero to One: Notes on Startups", 19.99, 6.5),
        ("User Experience Design Principles", 39.99, 14.0),
        ("Financial Intelligence for Founders", 26.99, 9.0),
    ],
    "Sports & Outdoors": [
        ("Anti-Burst Gym Exercise Ball with Pump", 22.99, 8.0),
        ("Adjustable Dumbbell Set 50 lbs", 179.99, 75.0),
        ("Non-Slip Pro Yoga Mat with Strap", 34.99, 12.0),
        ("Resistance Bands Set (5 Levels)", 19.99, 6.5),
        ("Ultralight Camping Hammock", 29.99, 10.0),
        ("Hydration Pack Running Backpack", 42.99, 15.0),
        ("Carbon Fiber Trekking Poles", 49.99, 18.0),
        ("Insulated Stainless Steel Shaker Bottle", 18.99, 6.0),
        ("Speed Jump Rope with Ball Bearings", 14.99, 4.5),
        ("Compact Deep Tissue Massage Gun", 89.99, 34.0),
    ],
    "Health & Beauty": [
        ("Sonic Electric Toothbrush with 4 Heads", 49.99, 17.0),
        ("Vitamin C + Hyaluronic Acid Face Serum", 28.99, 9.0),
        ("Natural Mineral Sunscreen SPF 50", 21.99, 7.0),
        ("Organic Argan Hair Repair Oil", 24.99, 8.0),
        ("Collagen Peptides Powder 16oz", 36.99, 13.0),
        ("Deep Hydration Night Cream", 32.99, 11.0),
        ("Beard Grooming Kit with Sandalwood Oil", 29.99, 10.0),
        ("Ultra-Quiet Cool Mist Humidifier", 39.99, 14.5),
        ("Daily Multivitamin for Active Adults", 22.99, 7.5),
        ("Exfoliating Coffee Body Scrub", 17.99, 5.5),
    ],
}

CITIES = ["New York", "San Francisco", "Austin", "Chicago", "Seattle", "Boston", "Denver", "Atlanta"]
OCCUPATIONS = [
    "Student",
    "Software Engineer",
    "Marketing Manager",
    "Graphic Designer",
    "Data Scientist",
    "Teacher",
    "Nurse",
    "Accountant",
    "Sales Executive",
    "Freelancer",
]

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Casey", "Avery",
    "Jamie", "Cameron", "Dakota", "Reese", "Quinn", "Skyler", "Kendall", "Peyton", "Logan", "Harper",
    "Emma", "Liam", "Olivia", "Noah", "Sophia", "Jackson", "Ava", "Aiden", "Isabella", "Lucas",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson",
    "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore", "Martin", "Jackson", "Thompson", "White",
]


def generate_dataset(
    num_products: int = 120,
    num_customers: int = 1000,
    min_purchases: int = 5500,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate reproducible marketing dataset with mathematical consistency."""
    rng = random.Random(seed)

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Generate Products (num_products >= 100)
    # ──────────────────────────────────────────────────────────────────────────
    products_raw: list[dict] = []
    prod_idx = 1

    # Base list from templates
    for category, items in PRODUCT_TEMPLATES.items():
        for base_name, base_price, base_cost in items:
            p_id = f"prod_{prod_idx:04d}"
            rating = round(rng.uniform(3.4, 4.9), 1)
            conv_rate = round(rng.uniform(0.018, 0.075), 4)
            initial_inventory = rng.randint(300, 800)

            products_raw.append({
                "product_id": p_id,
                "product_name": base_name,
                "category": category,
                "price": round(base_price, 2),
                "cost": round(base_cost, 2),
                "units_sold": 0,       # updated after purchase generation
                "revenue": 0.0,        # updated after purchase generation
                "average_rating": rating,
                "review_count": 0,     # updated after purchase generation
                "conversion_rate": conv_rate,
                "inventory": initial_inventory,
            })
            prod_idx += 1

    # Expand to num_products if needed
    while len(products_raw) < num_products:
        category = rng.choice(CATEGORIES)
        template_name, base_price, base_cost = rng.choice(PRODUCT_TEMPLATES[category])
        variant_suffix = rng.choice(["Plus", "Max", "Edition", "Classic", "Mini", "Ultra", "Lite"])
        p_id = f"prod_{prod_idx:04d}"
        multiplier = round(rng.uniform(0.85, 1.35), 2)
        price = round(base_price * multiplier, 2)
        cost = round(min(price * 0.65, base_cost * multiplier), 2)
        rating = round(rng.uniform(3.2, 4.8), 1)
        conv_rate = round(rng.uniform(0.015, 0.065), 4)
        initial_inventory = rng.randint(250, 700)

        products_raw.append({
            "product_id": p_id,
            "product_name": f"{template_name} ({variant_suffix})",
            "category": category,
            "price": price,
            "cost": cost,
            "units_sold": 0,
            "revenue": 0.0,
            "average_rating": rating,
            "review_count": 0,
            "conversion_rate": conv_rate,
            "inventory": initial_inventory,
        })
        prod_idx += 1

    # Popularity weights (power-law distribution for realistic popularity)
    product_weights: list[float] = [1.0 / ((i + 1) ** 0.65) for i in range(len(products_raw))]
    total_weight = sum(product_weights)
    norm_product_weights = [w / total_weight for w in product_weights]

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Generate Customers (num_customers >= 1000)
    # ──────────────────────────────────────────────────────────────────────────
    # Distribution of customer types:
    # VIP: ~6%, Regular: ~28%, Occasional: ~38%, New: ~18%, Inactive: ~10%
    type_distribution = ["VIP"] * 6 + ["Regular"] * 28 + ["Occasional"] * 38 + ["New"] * 18 + ["Inactive"] * 10

    customers_raw: list[dict] = []
    customer_target_orders: dict[str, int] = {}

    for c_idx in range(1, num_customers + 1):
        c_id = f"cust_{c_idx:05d}"
        c_type = rng.choice(type_distribution)
        occupation = rng.choice(OCCUPATIONS)
        city = rng.choice(CITIES)

        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{c_idx}@example.com"

        # Age pattern: Students are younger (18-25)
        if occupation == "Student":
            age = rng.randint(18, 25)
        else:
            age = rng.randint(23, 68)

        # Target order counts based on customer_type
        if c_type == "VIP":
            target_orders = rng.randint(10, 24)
        elif c_type == "Regular":
            target_orders = rng.randint(4, 9)
        elif c_type == "Occasional":
            target_orders = rng.randint(2, 3)
        elif c_type == "New":
            target_orders = 1
        else:  # Inactive
            target_orders = 0

        customer_target_orders[c_id] = target_orders

        customers_raw.append({
            "customer_id": c_id,
            "name": name,
            "email": email,
            "age": age,
            "occupation": occupation,
            "city": city,
            "customer_type": c_type,
            "total_spend": 0.0,       # updated after purchase generation
            "total_orders": 0,        # updated after purchase generation
            "last_purchase_date": "", # updated after purchase generation
        })

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Generate Purchases (>= 5000)
    # ──────────────────────────────────────────────────────────────────────────
    prod_lookup = {p["product_id"]: p for p in products_raw}
    cust_lookup = {c["customer_id"]: c for c in customers_raw}

    purchases_raw: list[dict] = []
    purchase_idx = 1
    base_date = datetime(2025, 1, 15)

    # Generate purchases per customer based on target_orders
    for c_id, num_orders in customer_target_orders.items():
        cust = cust_lookup[c_id]
        is_student = cust["occupation"] == "Student"
        is_vip = cust["customer_type"] == "VIP"

        for _ in range(num_orders):
            p_id = f"pur_{purchase_idx:06d}"

            # Student purchasing pattern: skewed towards books, electronics, fashion and budget < $100
            if is_student and rng.random() < 0.70:
                student_eligible = [
                    p for p in products_raw
                    if p["price"] < 100.0 and p["category"] in ["Books & Media", "Electronics", "Fashion"]
                ]
                selected_prod = rng.choice(student_eligible) if student_eligible else rng.choice(products_raw)
                quantity = 1 if rng.random() < 0.85 else 2
            elif is_vip and rng.random() < 0.50:
                # VIPs often buy premium products or multi-item baskets
                vip_eligible = [p for p in products_raw if p["price"] >= 50.0]
                selected_prod = rng.choice(vip_eligible) if vip_eligible else rng.choice(products_raw)
                quantity = rng.randint(1, 4)
            else:
                # Weighted popularity selection
                selected_prod = rng.choices(products_raw, weights=norm_product_weights, k=1)[0]
                quantity = rng.randint(1, 3)

            # Realistic purchase date spread across 365 days
            days_offset = rng.randint(0, 365)
            purchase_dt = base_date + timedelta(days=days_offset)
            purchase_date_str = purchase_dt.strftime("%Y-%m-%d")

            unit_price = selected_prod["price"]
            total_amount = round(quantity * unit_price, 2)

            purchases_raw.append({
                "purchase_id": p_id,
                "customer_id": c_id,
                "product_id": selected_prod["product_id"],
                "purchase_date": purchase_date_str,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_amount": total_amount,
            })
            purchase_idx += 1

    # Ensure minimum purchases threshold is met
    active_cust_ids = [c["customer_id"] for c in customers_raw if customer_target_orders[c["customer_id"]] > 0]
    while len(purchases_raw) < min_purchases:
        c_id = rng.choice(active_cust_ids)
        selected_prod = rng.choices(products_raw, weights=norm_product_weights, k=1)[0]
        quantity = rng.randint(1, 2)
        unit_price = selected_prod["price"]
        total_amount = round(quantity * unit_price, 2)
        days_offset = rng.randint(0, 365)
        purchase_dt = base_date + timedelta(days=days_offset)

        purchases_raw.append({
            "purchase_id": f"pur_{purchase_idx:06d}",
            "customer_id": c_id,
            "product_id": selected_prod["product_id"],
            "purchase_date": purchase_dt.strftime("%Y-%m-%d"),
            "quantity": quantity,
            "unit_price": unit_price,
            "total_amount": total_amount,
        })
        purchase_idx += 1

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Synchronise Customer and Product Aggregates for Exact Consistency
    # ──────────────────────────────────────────────────────────────────────────
    purchases_df = pd.DataFrame(purchases_raw)

    # Customer aggregates
    cust_spend = purchases_df.groupby("customer_id")["total_amount"].sum().to_dict()
    cust_orders = purchases_df.groupby("customer_id")["purchase_id"].count().to_dict()
    cust_latest = purchases_df.groupby("customer_id")["purchase_date"].max().to_dict()

    for c in customers_raw:
        c_id = c["customer_id"]
        c["total_spend"] = round(cust_spend.get(c_id, 0.0), 2)
        c["total_orders"] = int(cust_orders.get(c_id, 0))
        c["last_purchase_date"] = cust_latest.get(c_id, "")

    # Product aggregates
    prod_units = purchases_df.groupby("product_id")["quantity"].sum().to_dict()
    prod_rev = purchases_df.groupby("product_id")["total_amount"].sum().to_dict()

    for p in products_raw:
        p_id = p["product_id"]
        units = int(prod_units.get(p_id, 0))
        rev = round(prod_rev.get(p_id, 0.0), 2)
        p["units_sold"] = units
        p["revenue"] = rev
        # Inventory is remaining stock after units sold, always positive
        p["inventory"] = max(15, p["inventory"] - units)
        # Reviews proportional to sales
        p["review_count"] = min(units, int(units * rng.uniform(0.12, 0.35)))

    products_df = pd.DataFrame(products_raw)
    customers_df = pd.DataFrame(customers_raw)

    return products_df, customers_df, purchases_df


def save_to_csv(
    products_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    purchases_df: pd.DataFrame,
    target_dir: Path = RAW_DIR,
) -> None:
    """Save datasets to CSV files."""
    target_dir.mkdir(parents=True, exist_ok=True)

    products_path = target_dir / "products.csv"
    customers_path = target_dir / "customers.csv"
    purchases_path = target_dir / "purchases.csv"

    products_df.to_csv(products_path, index=False)
    customers_df.to_csv(customers_path, index=False)
    purchases_df.to_csv(purchases_path, index=False)

    print(f"[OK] Saved products:  {len(products_df):>6} rows -> {products_path}")
    print(f"[OK] Saved customers: {len(customers_df):>6} rows -> {customers_path}")
    print(f"[OK] Saved purchases: {len(purchases_df):>6} rows -> {purchases_path}")


def main() -> None:
    print("Generating reproducible synthetic marketing datasets (seed=42)...")
    products_df, customers_df, purchases_df = generate_dataset(
        num_products=120,
        num_customers=1000,
        min_purchases=5500,
        seed=SEED,
    )

    print("Validating generated datasets against all integrity rules...")
    validate_all(products_df, customers_df, purchases_df)
    print("[OK] All mathematical and integrity constraints verified.")

    save_to_csv(products_df, customers_df, purchases_df)
    print("\nDataset generation completed successfully.")


if __name__ == "__main__":
    main()
