#!/usr/bin/env python3
"""Seed initial plant inventory data into Firestore for greenhouse-agent."""

from google.cloud import firestore

# Hardcode project ID as instructed (Agent Platform returns project number from default credentials)
PROJECT_ID = "qwiklabs-gcp-03-087f73aea569"

SEEDED_PLANTS = [
    {
        "id": "monstera-deliciosa",
        "name": "Monstera Deliciosa",
        "species": "Monstera deliciosa",
        "category": "Tropical",
        "light_requirement": "Bright, indirect sunlight",
        "watering_schedule": "Water every 1-2 weeks, letting soil dry out halfway",
        "difficulty": "Easy",
        "price": 34.99,
        "stock": 15,
        "description": "Famous for its natural leaf fenestrations. Vibrant, fast-growing tropical indoor plant.",
    },
    {
        "id": "snake-plant",
        "name": "Snake Plant (Sansevieria)",
        "species": "Dracaena trifasciata",
        "category": "Succulent",
        "light_requirement": "Tolerates low light, thrives in medium to bright indirect light",
        "watering_schedule": "Water every 2-3 weeks; allow soil to dry completely between waterings",
        "difficulty": "Beginner",
        "price": 24.50,
        "stock": 20,
        "description": "Extremely hardy, air-purifying plant with architectural upright green leaves.",
    },
    {
        "id": "fiddle-leaf-fig",
        "name": "Fiddle Leaf Fig",
        "species": "Ficus lyrata",
        "category": "Tree",
        "light_requirement": "Abundant bright, filtered light (avoid harsh direct midday sun)",
        "watering_schedule": "Water thoroughly once top 2 inches of soil feel dry, roughly once a week",
        "difficulty": "Moderate",
        "price": 49.99,
        "stock": 8,
        "description": "Iconic interior tree with large, violin-shaped glossy leaves.",
    },
    {
        "id": "golden-pothos",
        "name": "Golden Pothos",
        "species": "Epipremnum aureum",
        "category": "Climbing",
        "light_requirement": "Low to bright indirect light",
        "watering_schedule": "Water every 7-10 days when soil feels dry",
        "difficulty": "Beginner",
        "price": 18.00,
        "stock": 25,
        "description": "Trailing vine with heart-shaped variegated leaves. Great for hanging baskets.",
    },
    {
        "id": "peace-lily",
        "name": "Peace Lily",
        "species": "Spathiphyllum",
        "category": "Flowering",
        "light_requirement": "Medium to low indirect light",
        "watering_schedule": "Keep soil lightly moist; water when leaves start to droop slightly",
        "difficulty": "Easy",
        "price": 28.00,
        "stock": 12,
        "description": "Deep green foliage with elegant white spathes. Excellent natural air cleaner.",
    },
]


def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("plants")

    for plant in SEEDED_PLANTS:
        doc_id = plant["id"]
        collection_ref.document(doc_id).set(plant)
        print(f"  ✓ Seeded plant: {plant['name']} ({doc_id})")

    print("\n✅ Successfully seeded all plant records into Firestore!")


if __name__ == "__main__":
    seed_database()
