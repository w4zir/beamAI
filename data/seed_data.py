"""
Seed script to populate the database with sample data for development.
Generates synthetic products, users, and events.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import uuid

# Add backend directory to path to import app modules
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.core.database import get_supabase_client

# Sample product categories and data
CATEGORIES = [
    "electronics",
    "fashion",
    "home",
    "sports",
    "books",
    "toys",
    "beauty",
    "automotive"
]

PRODUCT_NAMES = {
    "electronics": [
        "Wireless Bluetooth Headphones",
        "Smart Watch Pro",
        "USB-C Charging Cable",
        "Wireless Mouse",
        "Mechanical Keyboard",
        "4K Monitor",
        "Portable Power Bank",
        "Bluetooth Speaker"
    ],
    "fashion": [
        "Cotton T-Shirt",
        "Denim Jeans",
        "Running Shoes",
        "Leather Jacket",
        "Summer Dress",
        "Winter Coat",
        "Sneakers",
        "Baseball Cap"
    ],
    "home": [
        "Coffee Maker",
        "Stand Mixer",
        "Air Fryer",
        "Vacuum Cleaner",
        "Table Lamp",
        "Throw Pillow",
        "Wall Clock",
        "Desk Organizer"
    ],
    "sports": [
        "Yoga Mat",
        "Dumbbell Set",
        "Basketball",
        "Tennis Racket",
        "Running Shorts",
        "Gym Bag",
        "Water Bottle",
        "Resistance Bands"
    ],
    "books": [
        "Science Fiction Novel",
        "Cookbook",
        "Biography",
        "Mystery Thriller",
        "Self-Help Guide",
        "History Book",
        "Poetry Collection",
        "Technical Manual"
    ],
    "toys": [
        "Building Blocks Set",
        "Action Figure",
        "Board Game",
        "Puzzle Set",
        "Remote Control Car",
        "Doll House",
        "Art Supplies Kit",
        "Educational Toy"
    ],
    "beauty": [
        "Face Moisturizer",
        "Lipstick Set",
        "Hair Shampoo",
        "Sunscreen Lotion",
        "Face Mask",
        "Perfume",
        "Nail Polish",
        "Makeup Brush Set"
    ],
    "automotive": [
        "Car Phone Mount",
        "Dash Cam",
        "Car Floor Mats",
        "Tire Pressure Gauge",
        "Car Charger",
        "Steering Wheel Cover",
        "Car Air Freshener",
        "Jump Starter"
    ]
}

DESCRIPTIONS = {
    "electronics": "High-quality electronic device with advanced features and modern design.",
    "fashion": "Stylish and comfortable clothing item perfect for everyday wear.",
    "home": "Essential home product that combines functionality with elegant design.",
    "sports": "Durable sports equipment designed for performance and comfort.",
    "books": "Engaging book that offers valuable insights and entertainment.",
    "toys": "Fun and educational toy that encourages creativity and learning.",
    "beauty": "Premium beauty product for your daily skincare and makeup routine.",
    "automotive": "Reliable automotive accessory to enhance your driving experience."
}


def generate_products(client, num_products=20):
    """Generate and insert sample products."""
    products = []
    
    for i in range(num_products):
        category = random.choice(CATEGORIES)
        product_names = PRODUCT_NAMES.get(category, ["Generic Product"])
        name = random.choice(product_names)
        
        product_id = f"prod_{uuid.uuid4().hex[:12]}"
        price = round(random.uniform(10.0, 500.0), 2)
        
        # Create products at different times (some older, some newer)
        days_ago = random.randint(0, 180)
        created_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
        
        product = {
            "id": product_id,
            "name": name,
            "description": DESCRIPTIONS.get(category, "A quality product."),
            "category": category,
            "price": price,
            "popularity_score": 0.0,
            "created_at": created_at
        }
        products.append(product)
    
    # Insert products in batches
    try:
        response = client.table("products").insert(products).execute()
        print(f"[OK] Inserted {len(products)} products")
        return [p["id"] for p in products]
    except Exception as e:
        print(f"[ERROR] Error inserting products: {e}")
        return []


def generate_users(client, num_users=10):
    """Generate and insert sample users."""
    users = []
    
    for i in range(num_users):
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        days_ago = random.randint(0, 365)
        created_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
        
        user = {
            "id": user_id,
            "created_at": created_at
        }
        users.append(user)
    
    try:
        response = client.table("users").insert(users).execute()
        print(f"[OK] Inserted {len(users)} users")
        return [u["id"] for u in users]
    except Exception as e:
        print(f"[ERROR] Error inserting users: {e}")
        return []


def generate_events(client, user_ids, product_ids, num_events=100):
    """Generate and insert sample events."""
    events = []
    event_types = ["view", "add_to_cart", "purchase"]
    sources = ["search", "recommendation", "direct"]
    
    for i in range(num_events):
        user_id = random.choice(user_ids)
        product_id = random.choice(product_ids)
        event_type = random.choices(
            event_types,
            weights=[0.7, 0.2, 0.1]  # More views than carts, more carts than purchases
        )[0]
        source = random.choice(sources)
        
        # Events spread over last 90 days
        days_ago = random.randint(0, 90)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        timestamp = (datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)).isoformat()
        
        event = {
            "user_id": user_id,
            "product_id": product_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "source": source
        }
        events.append(event)
    
    # Insert events in batches of 50
    batch_size = 50
    inserted = 0
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        try:
            response = client.table("events").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"[ERROR] Error inserting events batch: {e}")
    
    print(f"[OK] Inserted {inserted} events")
    return inserted


def main():
    """Main function to seed the database."""
    print("Starting database seeding...")
    print("-" * 50)
    
    client = get_supabase_client()
    if not client:
        print("[ERROR] Failed to connect to Supabase. Check your .env file.")
        sys.exit(1)
    
    # Check if tables exist by trying to query them
    try:
        client.table("products").select("id").limit(1).execute()
    except Exception as e:
        print(f"[ERROR] Tables may not exist. Run migrations first.")
        print(f"  Error: {e}")
        sys.exit(1)
    
    # Generate data
    print("\nGenerating products...")
    product_ids = generate_products(client, num_products=20)
    
    print("\nGenerating users...")
    user_ids = generate_users(client, num_users=10)
    
    print("\nGenerating events...")
    generate_events(client, user_ids, product_ids, num_events=100)
    
    print("\n" + "-" * 50)
    print("[OK] Database seeding completed successfully!")
    print(f"  - Products: {len(product_ids)}")
    print(f"  - Users: {len(user_ids)}")
    print(f"  - Events: 100")


if __name__ == "__main__":
    main()

