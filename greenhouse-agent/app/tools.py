"""Firestore backend tools for greenhouse-agent."""

import datetime
from google.adk.tools import ToolContext
from google.cloud import firestore

# Hardcode project ID as instructed (Agent Platform returns project number from default credentials)
PROJECT_ID = "qwiklabs-gcp-03-087f73aea569"
BUCKET_NAME = "greenhouse-plants-qwiklabs-gcp-03-087f73aea569"

_db = None


def get_firestore_client() -> firestore.Client:
    """Get or initialize the Firestore client with hardcoded project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def list_plants(category: str = "") -> list[dict]:
    """List greenhouse plants from the inventory in Firestore.

    Args:
        category: Optional category filter (e.g. 'Tropical', 'Succulent', 'Tree', 'Climbing', 'Flowering').
                  If empty, returns all plants in inventory.

    Returns:
        A list of plant dictionaries containing id, name, category, price, stock, and difficulty.
    """
    db = get_firestore_client()
    collection_ref = db.collection("plants")

    if category:
        docs = collection_ref.where("category", "==", category).stream()
    else:
        docs = collection_ref.stream()

    results = []
    for doc in docs:
        results.append(doc.to_dict())

    if not results and category:
        # Fallback to case-insensitive match across all
        all_docs = collection_ref.stream()
        for doc in all_docs:
            data = doc.to_dict()
            if data.get("category", "").lower() == category.lower():
                results.append(data)

    return results


def get_plant(plant_id_or_name: str) -> dict:
    """Get detailed information, care requirements, and stock for a specific plant.

    Args:
        plant_id_or_name: The plant document ID (e.g., 'monstera-deliciosa', 'snake-plant')
                          or common name (e.g., 'Monstera Deliciosa').

    Returns:
        A dictionary with full plant details including watering schedule, light requirements,
        price, stock, and care tips. If not found, returns an error message dictionary.
    """
    db = get_firestore_client()
    collection_ref = db.collection("plants")

    # Try direct ID lookup
    clean_id = plant_id_or_name.lower().strip().replace(" ", "-")
    doc_ref = collection_ref.document(clean_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()

    # Search by common name or species
    docs = collection_ref.stream()
    search_term = plant_id_or_name.lower().strip()
    for d in docs:
        data = d.to_dict()
        if (
            search_term in data.get("name", "").lower()
            or search_term in data.get("id", "").lower()
            or search_term in data.get("species", "").lower()
        ):
            return data

    return {"error": f"Plant '{plant_id_or_name}' not found in greenhouse inventory."}


def save_plant(
    plant_id: str,
    name: str,
    category: str,
    light_requirement: str,
    watering_schedule: str,
    difficulty: str,
    price: float,
    stock: int,
    description: str,
) -> str:
    """Add a new plant or update existing plant information and inventory stock in Firestore.

    Args:
        plant_id: Unique identifier for the plant, lowercase with hyphens (e.g., 'calathea-orbifolia').
        name: Common name of the plant (e.g., 'Calathea Orbifolia').
        category: Plant category (e.g., 'Tropical', 'Foliage', 'Succulent', 'Tree').
        light_requirement: Light conditions needed (e.g., 'Medium to bright indirect light').
        watering_schedule: Watering instructions (e.g., 'Keep soil evenly moist, water weekly').
        difficulty: Care difficulty level ('Beginner', 'Easy', 'Moderate', 'Expert').
        price: Retail price in USD (e.g., 29.99).
        stock: Current available quantity in inventory.
        description: Brief description and care tips for the plant.

    Returns:
        A confirmation message indicating the plant was successfully saved to Firestore.
    """
    db = get_firestore_client()
    doc_ref = db.collection("plants").document(plant_id.lower().strip())
    plant_data = {
        "id": plant_id.lower().strip(),
        "name": name,
        "category": category,
        "light_requirement": light_requirement,
        "watering_schedule": watering_schedule,
        "difficulty": difficulty,
        "price": float(price),
        "stock": int(stock),
        "description": description,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    doc_ref.set(plant_data, merge=True)
    return f"Successfully saved plant '{name}' (ID: {plant_id}) to Firestore."


def log_plant_care(plant_id: str, action: str, notes: str = "") -> str:
    """Log a plant care activity (such as watering, fertilizing, repotting, pruning) in Firestore.

    Args:
        plant_id: The ID of the plant receiving care (e.g., 'monstera-deliciosa').
        action: The care action performed (e.g., 'watered', 'fertilized', 'repotted', 'pruned').
        notes: Optional observation or notes (e.g., 'Soil was dry, gave 500ml water').

    Returns:
        A confirmation message indicating the care log was recorded.
    """
    db = get_firestore_client()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_entry = {
        "action": action,
        "notes": notes,
        "timestamp": timestamp,
    }
    db.collection("plants").document(plant_id.lower().strip()).collection("care_logs").add(log_entry)
    return f"Logged care activity '{action}' for plant '{plant_id}' at {timestamp}."


def parse_watering_interval_days(schedule_text: str) -> int:
    """Helper to parse estimated interval days from schedule string."""
    import re

    text = schedule_text.lower()
    m_weeks_range = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*weeks?", text)
    if m_weeks_range:
        return (int(m_weeks_range.group(1)) + int(m_weeks_range.group(2))) * 7 // 2

    m_weeks = re.search(r"(\d+)\s*weeks?", text)
    if m_weeks:
        return int(m_weeks.group(1)) * 7

    m_days_range = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*days?", text)
    if m_days_range:
        return (int(m_days_range.group(1)) + int(m_days_range.group(2))) // 2

    m_days = re.search(r"(\d+)\s*days?", text)
    if m_days:
        return int(m_days.group(1))

    return 7


def calculate_next_watering(plant_id_or_name: str) -> dict:
    """Calculate days elapsed since last watering and the next recommended watering date.

    Args:
        plant_id_or_name: The plant document ID (e.g. 'monstera-deliciosa', 'snake-plant')
                          or common name (e.g. 'Monstera Deliciosa').

    Returns:
        A dictionary containing the watering status, last watered date, days elapsed,
        next scheduled watering date, days remaining, and care advice.
    """
    db = get_firestore_client()
    plant = get_plant(plant_id_or_name)
    if "error" in plant:
        return plant

    plant_id = plant.get("id", plant_id_or_name.lower().strip().replace(" ", "-"))
    plant_name = plant.get("name", plant_id)
    schedule_str = plant.get("watering_schedule", "Water weekly when soil feels dry")
    interval_days = parse_watering_interval_days(schedule_str)

    # Check care_logs subcollection for latest watering log
    care_logs_ref = db.collection("plants").document(plant_id).collection("care_logs")
    logs = care_logs_ref.where("action", "==", "watered").stream()

    latest_log = None
    for log in logs:
        data = log.to_dict()
        if latest_log is None or data.get("timestamp", "") > latest_log.get("timestamp", ""):
            latest_log = data

    now = datetime.datetime.now(datetime.timezone.utc)

    if not latest_log:
        return {
            "plant_id": plant_id,
            "plant_name": plant_name,
            "status": "NO_PREVIOUS_LOGS",
            "watering_schedule": schedule_str,
            "recommended_interval_days": interval_days,
            "advice": (
                f"No previous watering records found for {plant_name}. "
                f"General guideline: {schedule_str}. "
                "Please check the soil moisture; if dry, water it and use log_plant_care to start tracking!"
            ),
        }

    last_watered_dt = datetime.datetime.fromisoformat(latest_log["timestamp"])
    days_elapsed = (now - last_watered_dt).days
    next_watering_dt = last_watered_dt + datetime.timedelta(days=interval_days)
    days_remaining = (next_watering_dt.date() - now.date()).days

    if days_remaining <= 0:
        status = "NEEDS_WATERING"
        advice = (
            f"🚨 {plant_name} was last watered {days_elapsed} day(s) ago (recommended every ~{interval_days} days). "
            f"It is due (or overdue by {abs(days_remaining)} day(s)). Check the soil and give it a thorough soak!"
        )
    elif days_remaining <= 2:
        status = "WATER_SOON"
        advice = (
            f"⚠️ {plant_name} will need watering soon (in {days_remaining} day(s) on {next_watering_dt.strftime('%Y-%m-%d')}). "
            "Keep an eye on the topsoil."
        )
    else:
        status = "OPTIMAL"
        advice = (
            f"✅ {plant_name} is in good shape! Watered {days_elapsed} day(s) ago. "
            f"Next watering expected in {days_remaining} day(s) on {next_watering_dt.strftime('%Y-%m-%d')}."
        )

    return {
        "plant_id": plant_id,
        "plant_name": plant_name,
        "status": status,
        "watering_schedule": schedule_str,
        "recommended_interval_days": interval_days,
        "last_watered": last_watered_dt.strftime("%Y-%m-%d %H:%M UTC"),
        "days_since_last_watered": days_elapsed,
        "next_watering_date": next_watering_dt.strftime("%Y-%m-%d"),
        "days_remaining": days_remaining,
        "advice": advice,
    }


def get_plant_environment(city: str) -> dict:
    """Fetch live real-world weather and humidity from the Open-Meteo public API to evaluate plant care conditions.

    Args:
        city: City name to look up weather and humidity for (e.g. 'San Francisco', 'New York', 'London', 'Taipei').

    Returns:
        A dictionary with location, live temperature, humidity, precipitation, and botanical advice for plants.
    """
    import json
    import os
    import urllib.parse
    import urllib.request

    # Optional API key support if configured in environment
    _api_key = os.getenv("WEATHER_API_KEY", "")

    try:
        # 1. Geocode city name to lat/lon using Open-Meteo Geocoding API
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        geo_req = urllib.request.Request(geo_url, headers={"User-Agent": "GreenhouseAgent/1.0"})
        with urllib.request.urlopen(geo_req, timeout=8) as geo_res:
            geo_data = json.loads(geo_res.read().decode())

        results = geo_data.get("results")
        if not results:
            return {"error": f"Could not find coordinates for city: '{city}'"}

        loc = results[0]
        lat = loc["latitude"]
        lon = loc["longitude"]
        loc_name = loc.get("name", city)
        country = loc.get("country", "")

        # 2. Fetch live environmental metrics
        forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation"
        f_req = urllib.request.Request(forecast_url, headers={"User-Agent": "GreenhouseAgent/1.0"})
        with urllib.request.urlopen(f_req, timeout=8) as f_res:
            forecast_data = json.loads(f_res.read().decode())

        current = forecast_data.get("current", {})
        temp_c = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")
        precip = current.get("precipitation", 0.0)

        # Convert Celsius to Fahrenheit
        temp_f = round((temp_c * 9 / 5) + 32, 1) if temp_c is not None else None

        # Botanical care assessments based on live conditions
        advice_points = []
        if temp_c is not None:
            if temp_c < 12:
                advice_points.append(
                    "⚠️ Low temperature alert: Cold stress risk for tropical plants (Monstera, Ficus, Calathea). "
                    "Keep indoors away from drafts and cold windowpanes."
                )
            elif temp_c > 32:
                advice_points.append(
                    "⚠️ High heat alert: Soil will dry rapidly. Water more frequently and protect delicate leaves from intense afternoon sun."
                )
            else:
                advice_points.append(
                    "✅ Temperature is in the comfortable sweet spot (15°C - 28°C) for most indoor houseplants."
                )

        if humidity is not None:
            if humidity < 40:
                advice_points.append(
                    "⚠️ Dry air alert (<40% RH): Tropical plants and ferns may suffer brown or crispy tips. "
                    "Run a humidifier or group plants together."
                )
            elif humidity > 75:
                advice_points.append(
                    "🌿 High humidity (>75% RH): Excellent for tropicals and mosses. "
                    "Ensure good room airflow to prevent mold or fungal issues."
                )
            else:
                advice_points.append("✅ Humidity is in a healthy range for typical household plants.")

        return {
            "location": f"{loc_name}, {country}".strip(", "),
            "latitude": lat,
            "longitude": lon,
            "temperature_c": temp_c,
            "temperature_f": temp_f,
            "relative_humidity_percent": humidity,
            "precipitation_mm": precip,
            "plant_care_advice": " ".join(advice_points),
        }
    except Exception as e:
        return {"error": f"Failed to fetch live climate data: {str(e)}"}


async def generate_plant_image(
    prompt: str, tool_context: ToolContext = None
) -> dict:
    """Generate a realistic botanical image for a plant or scene using gemini-3.1-flash-lite-image in the global region.

    The image is saved as an artifact in the Playground's Artifacts panel and uploaded directly to public Cloud Storage.

    Args:
        prompt: Description of the plant or greenhouse item to visualize (e.g. 'Lush Monstera Deliciosa in a terracotta pot').
        tool_context: ADK ToolContext to record the artifact for the Playground UI.

    Returns:
        A dictionary with the public HTTPS URL in Cloud Storage, artifact filename, and status.
    """
    import re
    import uuid
    from google import genai
    from google.cloud import storage
    from google.genai import types

    # 1. Generate image using gemini-3.1-flash-lite-image in global region
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"High quality, realistic botanical photograph of: {prompt}",
    )

    image_bytes = None
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                break
        if image_bytes:
            break

    if not image_bytes:
        return {"error": "Failed to generate image bytes from model response."}

    # Generate a descriptive filename
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", prompt.lower()[:30]).strip("_")
    filename = f"{slug}_{uuid.uuid4().hex[:6]}.jpg"

    # (1) Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
    artifact_saved = False
    if tool_context is not None:
        try:
            part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            await tool_context.save_artifact(filename=filename, artifact=part)
            artifact_saved = True
        except Exception:
            pass

    # (2) Upload in-memory image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    return {
        "filename": filename,
        "public_url": public_url,
        "artifact_saved": artifact_saved,
        "message": f"Successfully generated botanical image and uploaded to {public_url}",
    }



