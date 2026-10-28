import os
import re
import json
import time
import math
import hashlib
from datetime import datetime, timezone
from urllib.parse import quote_plus
import requests

# Konfigurasi Environment Variables
AMAZON_TAG = os.environ.get("AMAZON_TAG", "yourtag-20").strip()
SITE_URL = os.environ.get("SITE_URL", "https://username.github.io/repo-name").rstrip("/")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "user/repo")

# Kunci verifikasi IndexNow deterministik
INDEXNOW_KEY = hashlib.md5(f"{REPO_NAME}_{AMAZON_TAG}_solar300".encode("utf-8")).hexdigest()

DB_PATH = "data/power_db.json"
DOCS_DIR = "docs"
GUIDES_DIR = os.path.join(DOCS_DIR, "calculators")
COMBOS_DIR = os.path.join(DOCS_DIR, "bundles")

HEADERS = {
    "User-Agent": "WattGuardSEOEngine/2.0 (https://github.com; contact@github.com)"
}

# Daftar Peralatan Berdaya Tinggi yang Membutuhkan Power Station >$300
APPLIANCE_LOADS = [
    {"name": "Full-Size Kitchen Refrigerator (25 Cu. Ft.)", "cat": "Home Outage Essential", "run_w": 180, "surge_w": 1200, "duty_cycle": 0.45, "default_hrs": 24, "plug": "NEMA 5-15 (120V)"},
    {"name": "1/2 HP Basement Sump Pump", "cat": "Flood & Storm Protection", "run_w": 1050, "surge_w": 2400, "duty_cycle": 0.25, "default_hrs": 18, "plug": "NEMA 5-15 (120V)"},
    {"name": "3/4 HP Heavy-Duty Sump Pump", "cat": "Flood & Storm Protection", "run_w": 1300, "surge_w": 3100, "duty_cycle": 0.25, "default_hrs": 18, "plug": "NEMA 5-15 / 5-20"},
    {"name": "CPAP Machine with Heated Humidifier & Tube", "cat": "Medical Night Backup", "run_w": 65, "surge_w": 110, "duty_cycle": 1.0, "default_hrs": 16, "plug": "12V DC / 120V AC Pure Sine"},
    {"name": "13,500 BTU RV Rooftop Air Conditioner", "cat": "RV & Overlanding Climate", "run_w": 1350, "surge_w": 3000, "duty_cycle": 0.65, "default_hrs": 8, "plug": "TT-30R (30A RV Plug)"},
    {"name": "15,000 BTU RV Heat Pump Air Conditioner", "cat": "RV & Overlanding Climate", "run_w": 1550, "surge_w": 3400, "duty_cycle": 0.65, "default_hrs": 8, "plug": "TT-30R (30A RV Plug)"},
    {"name": "10,000 BTU Portable Dual-Hose Room Air Conditioner", "cat": "Summer Heatwave Backup", "run_w": 980, "surge_w": 1850, "duty_cycle": 0.70, "default_hrs": 8, "plug": "NEMA 5-15 (120V)"},
    {"name": "Deep Chest Freezer (15 Cu. Ft.)", "cat": "Food Preservation Backup", "run_w": 120, "surge_w": 950, "duty_cycle": 0.35, "default_hrs": 48, "plug": "NEMA 5-15 (120V)"},
    {"name": "Starlink High-Performance Dish + Home Office Setup", "cat": "Remote Work & Off-Grid Comms", "run_w": 165, "surge_w": 260, "duty_cycle": 1.0, "default_hrs": 12, "plug": "120V Pure Sine / High-Output USB-C PD"},
    {"name": "1/2 HP Submersible Deep Well Water Pump", "cat": "Off-Grid Homestead Water", "run_w": 1100, "surge_w": 2800, "duty_cycle": 0.20, "default_hrs": 24, "plug": "120V / 240V Split-Phase"},
    {"name": "1,500W Ceramic Space Heater (Low/High Mode)", "cat": "Winter Freeze Emergency", "run_w": 1500, "surge_w": 1550, "duty_cycle": 0.60, "default_hrs": 6, "plug": "NEMA 5-15 (120V)"},
    {"name": "Wood Pellet Grill & Smoker (Auger + Igniter)", "cat": "Tailgating & Outdoor Cooking", "run_w": 95, "surge_w": 450, "duty_cycle": 0.80, "default_hrs": 12, "plug": "NEMA 5-15 (120V)"},
    {"name": "Commercial Dual-Boiler Espresso Machine", "cat": "Mobile Coffee Cart & Camping", "run_w": 1450, "surge_w": 1600, "duty_cycle": 0.40, "default_hrs": 6, "plug": "NEMA 5-15 / 5-20"},
    {"name": "5-LPM Home Oxygen Concentrator", "cat": "Critical Medical Backup", "run_w": 380, "surge_w": 600, "duty_cycle": 1.0, "default_hrs": 12, "plug": "120V Hospital-Grade Pure Sine"},
    {"name": "Gas Furnace Blower Fan Motor (1/2 HP)", "cat": "Winter Home Heating Backup", "run_w": 650, "surge_w": 1600, "duty_cycle": 0.45, "default_hrs": 24, "plug": "Transfer Switch / Generator Inlet"},
    {"name": "Portable Induction Cooktop (1,800W Burner)", "cat": "Vanlife & Off-Grid Kitchen", "run_w": 1800, "surge_w": 1900, "duty_cycle": 0.50, "default_hrs": 2, "plug": "NEMA 5-15 (120V)"},
    {"name": "1,200W Inverter Microwave Oven", "cat": "Emergency Kitchen Appliance", "run_w": 1350, "surge_w": 2100, "duty_cycle": 0.50, "default_hrs": 1, "plug": "NEMA 5-15 (120V)"},
    {"name": "12V/120V Dual-Zone 75L Overland Fridge Freezer", "cat": "Overlanding & Camping", "run_w": 65, "surge_w": 180, "duty_cycle": 0.35, "default_hrs": 72, "plug": "12V Anderson / Car Port"},
    {"name": " Portable Jobsite Table Saw (15-Amp Motor)", "cat": "Off-Grid Contractor Power", "run_w": 1800, "surge_w": 3600, "duty_cycle": 0.30, "default_hrs": 4, "plug": "NEMA 5-20 (20A)"},
    {"name": "Level 1 / Portable EV Emergency Range Extender", "cat": "Roadside EV Backup", "run_w": 1440, "surge_w": 1600, "duty_cycle": 1.0, "default_hrs": 3, "plug": "NEMA 5-15 / TT-30 Grounded"},
    {"name": "70-Pint Basement Dehumidifier", "cat": "Moisture & Mold Prevention", "run_w": 680, "surge_w": 1400, "duty_cycle": 0.60, "default_hrs": 12, "plug": "NEMA 5-15 (120V)"},
    {"name": "Saltwater Reef Aquarium Life-Support (Heater + Return Pump)", "cat": "Aquarium Outage Protection", "run_w": 350, "surge_w": 650, "duty_cycle": 0.70, "default_hrs": 24, "plug": "UPS Pure Sine Wave"},
    {"name": " Tankless Natural Gas Water Heater Igniter & Vent", "cat": "Home Hot Water Backup", "run_w": 125, "surge_w": 300, "duty_cycle": 0.30, "default_hrs": 48, "plug": "NEMA 5-15 UPS"},
    {"name": "Electric Hospital Bed + Alternating Pressure Mattress", "cat": "Home Healthcare Backup", "run_w": 180, "surge_w": 750, "duty_cycle": 0.50, "default_hrs": 24, "plug": "120V Pure Sine Wave"},
    {"name": "Garage Door Opener (3/4 HP Belt Drive) + Home Security", "cat": "Home Access & Security", "run_w": 850, "surge_w": 1700, "duty_cycle": 0.15, "default_hrs": 24, "plug": "NEMA 5-15 (120V)"},
    {"name": " Pellet Stove Heating System (Auger + Convection Blower)", "cat": "Winter Cabin Heating", "run_w": 160, "surge_w": 520, "duty_cycle": 0.75, "default_hrs": 24, "plug": "120V Pure Sine Wave"},
    {"name": "4K Home Theater Projector + Gaming Desktop Rig", "cat": "High-Draw Entertainment", "run_w": 720, "surge_w": 1100, "duty_cycle": 1.0, "default_hrs": 5, "plug": "120V Pure Sine UPS"},
    {"name": "RV 30-Amp Shore Power Full Cabin Hookup", "cat": "Boondocking & Dry Camping", "run_w": 1600, "surge_w": 3500, "duty_cycle": 0.50, "default_hrs": 12, "plug": "NEMA TT-30R"},
    {"name": "240V Split-Phase Home Subpanel (Essential Circuits)", "cat": "Whole-Home Partial Backup", "run_w": 2400, "surge_w": 5500, "duty_cycle": 0.45, "default_hrs": 24, "plug": "NEMA L14-30R (30A 240V)"},
    {"name": "Food Truck Commercial Prep Fridge + POS Terminal", "cat": "Mobile Business Power", "run_w": 580, "surge_w": 1800, "duty_cycle": 0.55, "default_hrs": 10, "plug": "NEMA 5-15 / TT-30"}
]


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "power-guide"


def load_db() -> dict:
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_db(db: dict):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def make_amazon_bestseller_300_url(query: str, min_price_cents: int = 30000) -> str:
    """
    Membuat URL afiliasi Amazon US dengan filter harga minimum di atas $300 (30000 cents),
    filter rating bintang 4+, dan pengurutan otomatis berdasarkan Best-Sellers.
    """
    encoded_q = quote_plus(query)
    return (
        f"https://www.amazon.com/s?k={encoded_q}"
        f"&rh=p_36%3A{min_price_cents}-%2Cp_72%3A1248873011"
        f"&s=exact-aware-popularity-rank&tag={AMAZON_TAG}"
    )


def fetch_live_solar_and_grid_telemetry() -> dict:
    """
    Mengambil data radiasi surya nyata dari Open-Meteo API & jumlah peringatan cuaca aktif dari US NOAA API.
    Tidak membutuhkan API Key.
    """
    telemetry = {
        "avg_peak_sun_hours": 4.8,
        "solar_mj_m2": 17.3,
        "active_us_weather_alerts": 142
    }
    try:
        # Koordinat tengah AS untuk benchmark radiasi matahari harian
        meteo_url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=37.09&longitude=-95.71"
            "&daily=shortwave_radiation_sum,sunshine_duration&timezone=UTC&forecast_days=1"
        )
        r = requests.get(meteo_url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            daily = r.json().get("daily", {})
            rad_list = daily.get("shortwave_radiation_sum", [])
            if rad_list and rad_list[0]:
                mj = float(rad_list[0])
                # 1 kWh/m2 (1 Peak Sun Hour) = 3.6 MJ/m2
                psh = round(max(3.5, min(7.2, mj / 3.6)), 1)
                telemetry["avg_peak_sun_hours"] = psh
                telemetry["solar_mj_m2"] = round(mj, 1)
    except Exception as e:
        print(f"[WARN] Open-Meteo fallback: {e}")

    try:
        noaa_url = "https://api.weather.gov/alerts/active/count"
        r_noaa = requests.get(noaa_url, headers=HEADERS, timeout=10)
        if r_noaa.status_code == 200:
            total_alerts = int(r_noaa.json().get("total", 142))
            telemetry["active_us_weather_alerts"] = total_alerts
    except Exception as e:
        print(f"[WARN] NOAA API fallback: {e}")

    return telemetry


def calculate_power_specs(item: dict, telemetry: dict) -> dict:
    run_w = item["run_w"]
    surge_w = item["surge_w"]
    duty = item["duty_cycle"]
    hrs = item["default_hrs"]

    # Konsumsi efektif per jam dengan mempertimbangkan siklus kerja kompresor/motor (duty cycle)
    effective_wh_per_hr = round(run_w * duty, 1)
    net_wh_needed = effective_wh_per_hr * hrs

    # Efisiensi Inverter Pure Sine Wave (85%) & Batas Aman Depth of Discharge LiFePO4 (90%)
    usable_factor = 0.85 * 0.90
    gross_wh_required = int(math.ceil(net_wh_needed / usable_factor / 50.0) * 50)
    gross_wh_required = max(1024, gross_wh_required)

    # Kebutuhan panel surya (Watt) untuk mengisi ulang penuh dalam 1 hari Peak Sun Hours
    psh = telemetry["avg_peak_sun_hours"]
    solar_input_w = int(math.ceil((gross_wh_required / (psh * 0.78)) / 100.0) * 100)
    solar_input_w = max(200, min(1600, solar_input_w))

    # Minimum output inverter kontinu dan surge
    min_inverter_w = max(1000, int(math.ceil(max(run_w * 1.25, surge_w * 0.55) / 200.0) * 200))

    slug = f"best-solar-generator-portable-power-station-for-{slugify(item['name'])}"

    return {
        "name": item["name"],
        "slug": slug,
        "cat": item["cat"],
        "run_w": run_w,
        "surge_w": surge_w,
        "duty_cycle_pct": int(duty * 100),
        "default_hrs": hrs,
        "plug": item["plug"],
        "effective_wh_per_hr": effective_wh_per_hr,
        "gross_wh_required": gross_wh_required,
        "min_inverter_w": min_inverter_w,
        "solar_input_w": solar_input_w,
        "peak_sun_hours": psh,
        "active_alerts": telemetry["active_us_weather_alerts"],
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }


def build_high_ticket_recommendations(spec: dict) -> list:
    wh = spec["gross_wh_required"]
    inv = spec["min_inverter_w"]
    solar_w = spec["solar_input_w"]
    name = spec["name"]

    if wh <= 1500 and inv <= 1800:
        primary_station = {
            "tier": "Primary Best-Selling Match ($449 - $799)",
            "badge": "Top-Ranked 1,000Wh-1,500Wh LiFePO4",
            "title": "1024Wh - 1536Wh LiFePO4 Portable Power Station (1800W AC / 3600W Surge)",
            "price_range": "$449 – $799",
            "desc": f"Delivers pure sine wave output with <20ms EPS auto-switchover and 3,000+ LiFePO4 battery cycles—sized to run {name} without overload trips.",
            "query": "1000Wh 1800W LiFePO4 portable power station solar generator",
            "min_cents": 38000,
            "cta": "Shop #1 Best-Selling 1000Wh+ Power Stations ($380+)"
        }
    elif wh <= 2600:
        primary_station = {
            "tier": "High-Capacity Home & RV Match ($899 - $1,599)",
            "badge": "2,048Wh+ High-Surge LiFePO4",
            "title": "2048Wh - 2560Wh LiFePO4 Solar Generator (2400W AC / 4800W Surge)",
            "price_range": "$899 – $1,599",
            "desc": f"Engineered for high-inrush inductive motor loads like {name}, featuring expandable battery ports and ultra-fast 1,800W AC wall recharging.",
            "query": "2000Wh 2400W LiFePO4 portable power station solar generator",
            "min_cents": 75000,
            "cta": "View Best-Selling 2000Wh+ Solar Generators ($750+)"
        }
    else:
        primary_station = {
            "tier": "Flagship Whole-Home & 30A RV System ($1,599 - $2,899)",
            "badge": "3,600Wh+ Heavy-Duty Backup",
            "title": "3600Wh Expandable Home Backup Power Station (3600W / 7200W Surge, 30A Outlet)",
            "price_range": "$1,599 – $2,899",
            "desc": f"Industrial-grade LiFePO4 backup station capable of sustaining {name} over multi-day grid blackouts with direct home transfer switch integration.",
            "query": "3600Wh LiFePO4 portable power station home battery backup",
            "min_cents": 120000,
            "cta": "Explore Flagship 3600Wh+ Backup Stations ($1,200+)"
        }

    return [
        primary_station,
        {
            "tier": "Solar Generator + Panel Bundle ($699 - $1,899)",
            "badge": f"Includes {solar_w}W Solar Array",
            "title": f"LiFePO4 Solar Generator Bundled with Bifacial Folding Solar Panels",
            "price_range": "$699 – $1,899",
            "desc": f"Complete off-grid recharging kit matched to replenish {wh}Wh daily in {spec['peak_sun_hours']} peak sun hours for continuous {name} operation.",
            "query": "LiFePO4 solar generator with 200W 400W solar panel bundle",
            "min_cents": 60000,
            "cta": "Compare Solar Generator + Panel Bundles ($600+)"
        },
        {
            "tier": "High-Efficiency Folding Solar Array ($329 - $699)",
            "badge": "23% Monocrystalline IP68",
            "title": "400W Portable Folding Monocrystalline Solar Panel (Universal MC4 / XT60)",
            "price_range": "$329 – $699",
            "desc": "Weatherproof IP68 folding solar array with adjustable kickstands for maximum MPPT charge controller input during extended outages.",
            "query": "400W portable folding solar panel for power station",
            "min_cents": 30000,
            "cta": "Check Best-Selling 400W Solar Panels ($300+)"
        },
        {
            "tier": "DIY Expandable Deep-Cycle Storage ($369 - $999)",
            "badge": "3,840Wh - 5,120Wh Raw Capacity",
            "title": "12V 300Ah / 48V 100Ah LiFePO4 Deep-Cycle Battery (Built-In 200A Smart BMS)",
            "price_range": "$369 – $999",
            "desc": f"Lowest cost-per-watt-hour expansion battery for long-duration {name} runtime when paired with a pure sine wave inverter charger.",
            "query": "12V 300Ah OR 48V 100Ah LiFePO4 battery BMS",
            "min_cents": 32000,
            "cta": "See Top-Rated 300Ah/48V LiFePO4 Batteries ($320+)"
        },
        {
            "tier": "Dual-Fuel Extended Blackout Backup ($449 - $1,199)",
            "badge": "Propane & Gasoline Hybrid",
            "title": "4000W - 5500W Quiet Dual-Fuel Inverter Generator (Electric Start, RV Ready)",
            "price_range": "$449 – $1,199",
            "desc": "Clean <3% THD pure sine power to run high-draw appliances or rapidly recharge your LiFePO4 battery bank during multi-day winter storms.",
            "query": "dual fuel inverter generator quiet electric start",
            "min_cents": 40000,
            "cta": "Shop Best-Selling Dual-Fuel Inverter Generators ($400+)"
        }
    ]


def build_appliance_page(spec: dict, all_specs: list):
    os.makedirs(GUIDES_DIR, exist_ok=True)
    name = spec["name"]
    page_url = f"{SITE_URL}/calculators/{spec['slug']}.html"
    products = build_high_ticket_recommendations(spec)

    cards_html = ""
    for p in products:
        amz_link = make_amazon_bestseller_300_url(p["query"], p["min_cents"])
        cards_html += f"""
        <div class="card">
            <div class="card-top">
                <span class="tier">{p['tier']}</span>
                <span class="badge">{p['badge']}</span>
            </div>
            <h3>{p['title']}</h3>
            <p>{p['desc']}</p>
            <div class="card-foot">
                <span class="price-est">Amazon Price Tier: <strong>{p['price_range']}</strong></span>
                <a href="{amz_link}" target="_blank" rel="nofollow sponsored noopener" class="btn">{p['cta']} &rarr;</a>
            </div>
        </div>
        """

    related_html = ""
    for other in all_specs[:9]:
        if other["name"] == name:
            continue
        related_html += f"""
        <a href="{SITE_URL}/calculators/{other['slug']}.html" class="rel-link">
            <strong>{other['name']}</strong>
            <span>Run: {other['run_w']}W &bull; Surge: {other['surge_w']}W &bull; Min Battery: {other['gross_wh_required']}Wh &rarr;</span>
        </a>
        """

    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"What size solar generator or portable power station do I need to run a {name}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"A {name} requires {spec['run_w']} continuous running watts and up to {spec['surge_w']} starting surge watts. Accounting for a {spec['duty_cycle_pct']}% duty cycle, 85% inverter efficiency, and 90% LiFePO4 depth of discharge, you need at least a {spec['gross_wh_required']}Wh portable power station with a {spec['min_inverter_w']}W pure sine wave inverter for {spec['default_hrs']} hours of backup."
                }
            },
            {
                "@type": "Question",
                "name": f"How many solar panels do I need to keep a {name} running off-grid?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"Based on an average of {spec['peak_sun_hours']} peak sun hours per day, we recommend at least {spec['solar_input_w']}W of portable monocrystalline solar panels to replenish the daily {spec['gross_wh_required']}Wh energy draw."
                }
            }
        ]
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>What Size Solar Generator to Run a {name}? ({spec['gross_wh_required']}Wh Sizing Guide)</title>
    <meta name="description" content="Exact battery Wh and inverter surge sizing for a {name} ({spec['run_w']}W running / {spec['surge_w']}W surge). Compare the #1 best-selling LiFePO4 portable power stations ($300+ tier) on Amazon.">
    <link rel="canonical" href="{page_url}">
    <script type="application/ld+json">{json.dumps(faq_schema)}</script>
    <style>
        :root {{ --bg: #090e17; --panel: #111827; --border: #1f2937; --text: #f8fafc; --muted: #94a3b8; --amber: #f59e0b; --amber-dark: #d97706; --green: #10b981; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.65; padding-bottom: 60px; }}
        header {{ background: #030712; border-bottom: 1px solid var(--border); padding: 18px 24px; }}
        .nav {{ max-width: 1120px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }}
        .brand {{ color: var(--text); font-weight: 800; font-size: 1.25rem; text-decoration: none; }}
        .brand span {{ color: var(--amber); }}
        .container {{ max-width: 1120px; margin: 32px auto; padding: 0 20px; }}
        .hero {{ background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 28px; margin-bottom: 28px; }}
        .pills {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
        .pill {{ background: #030712; border: 1px solid var(--border); color: var(--amber); font-size: 0.78rem; padding: 4px 12px; border-radius: 999px; font-weight: 600; }}
        h1 {{ font-size: 1.88rem; line-height: 1.25; margin-bottom: 12px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-top: 22px; }}
        .m-box {{ background: #030712; border: 1px solid var(--border); padding: 16px; border-radius: 10px; }}
        .m-box span {{ display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 4px; }}
        .m-box strong {{ font-size: 1.45rem; color: var(--green); }}
        .calc {{ background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 24px; margin-bottom: 36px; }}
        .calc-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 16px; }}
        label {{ display: block; font-size: 0.84rem; color: var(--muted); margin-bottom: 6px; }}
        input, select {{ width: 100%; padding: 11px; border-radius: 8px; background: #030712; color: #fff; border: 1px solid var(--border); font-size: 0.95rem; }}
        .calc-res {{ margin-top: 20px; padding: 18px; background: #030712; border-left: 4px solid var(--amber); border-radius: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; }}
        .sec-title {{ font-size: 1.45rem; margin: 36px 0 18px; border-left: 4px solid var(--amber); padding-left: 12px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
        .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 22px; display: flex; flex-direction: column; justify-content: space-between; }}
        .card-top {{ display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
        .tier {{ font-size: 0.75rem; text-transform: uppercase; color: var(--amber); font-weight: 700; }}
        .badge {{ background: #030712; color: var(--green); font-size: 0.74rem; padding: 3px 8px; border-radius: 4px; border: 1px solid #059669; }}
        .card h3 {{ font-size: 1.12rem; margin-bottom: 10px; color: #fff; }}
        .card p {{ color: var(--muted); font-size: 0.92rem; margin-bottom: 18px; }}
        .price-est {{ display: block; font-size: 0.85rem; color: #cbd5e1; margin-bottom: 10px; }}
        .btn {{ display: block; text-align: center; background: var(--amber); color: #030712; font-weight: 800; text-decoration: none; padding: 13px 16px; border-radius: 8px; transition: background 0.15s; }}
        .btn:hover {{ background: var(--amber-dark); color: #fff; }}
        .rel-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-top: 16px; }}
        .rel-link {{ background: var(--panel); border: 1px solid var(--border); padding: 14px; border-radius: 10px; text-decoration: none; color: var(--text); display: block; }}
        .rel-link strong {{ display: block; font-size: 0.95rem; margin-bottom: 4px; color: #fff; }}
        .rel-link span {{ font-size: 0.81rem; color: var(--muted); }}
        footer {{ max-width: 1120px; margin: 50px auto 0; padding: 24px 20px 0; border-top: 1px solid var(--border); text-align: center; color: var(--muted); font-size: 0.82rem; }}
    </style>
</head>
<body>
    <header>
        <div class="nav">
            <a href="{SITE_URL}/" class="brand">Watt<span>Guard</span>300</a>
            <a href="{SITE_URL}/" style="color: var(--muted); text-decoration: none; font-size: 0.9rem;">&larr; All Appliance Calculators</a>
        </div>
    </header>
    <main class="container">
        <section class="hero">
            <div class="pills">
                <span class="pill">Category: {spec['cat']}</span>
                <span class="pill">Plug Type: {spec['plug']}</span>
                <span class="pill">Duty Cycle: {spec['duty_cycle_pct']}%</span>
                <span class="pill">US Solar Avg: {spec['peak_sun_hours']} Peak Sun Hrs</span>
                <span class="pill">Active NOAA Grid/Weather Alerts: {spec['active_alerts']}</span>
            </div>
            <h1>What Size Solar Generator & Portable Power Station Runs a {name}?</h1>
            <p style="color: var(--muted);">Complete engineering load analysis for powering a <strong>{name}</strong> during grid blackouts or off-grid operation, including starting compressor/motor surge requirements, LiFePO4 battery depth-of-discharge math, and compatible best-selling hardware.</p>
            <div class="metrics">
                <div class="m-box">
                    <span>Running / Surge Watts</span>
                    <strong>{spec['run_w']}W / {spec['surge_w']}W</strong>
                </div>
                <div class="m-box">
                    <span>Min Battery for {spec['default_hrs']} Hrs</span>
                    <strong>{spec['gross_wh_required']} Wh</strong>
                </div>
                <div class="m-box">
                    <span>Min Pure Sine Inverter</span>
                    <strong>{spec['min_inverter_w']}W AC</strong>
                </div>
                <div class="m-box">
                    <span>Recommended Solar Input</span>
                    <strong>{spec['solar_input_w']}W Array</strong>
                </div>
            </div>
        </section>

        <section class="calc">
            <h2 style="font-size: 1.25rem;">Interactive {name} Runtime & Battery Wh Sizing Calculator</h2>
            <div class="calc-grid">
                <div>
                    <label for="runWatts">Running Wattage (W)</label>
                    <input type="number" id="runWatts" value="{spec['run_w']}" onchange="recalcPower()" onkeyup="recalcPower()">
                </div>
                <div>
                    <label for="hoursInput">Desired Backup Hours</label>
                    <input type="number" id="hoursInput" value="{spec['default_hrs']}" onchange="recalcPower()" onkeyup="recalcPower()">
                </div>
                <div>
                    <label for="dutySelect">Compressor / Motor Duty Cycle</label>
                    <select id="dutySelect" onchange="recalcPower()">
                        <option value="{spec['duty_cycle_pct'] / 100.0}">Default ({spec['duty_cycle_pct']}% Active Cycling)</option>
                        <option value="1.0">100% Continuous Constant Load</option>
                        <option value="0.5">50% Moderate Cycling</option>
                        <option value="0.35">35% Eco / Well-Insulated Cycling</option>
                    </select>
                </div>
            </div>
            <div class="calc-res">
                <div>
                    <span style="font-size: 0.84rem; color: var(--muted);">Required LiFePO4 Battery Capacity (Includes 85% Inverter & 90% DoD Margin):</span>
                    <div id="whResult" style="font-size: 1.45rem; font-weight: 800; color: var(--amber);">{spec['gross_wh_required']} Wh Minimum Capacity</div>
                </div>
                <a href="{make_amazon_bestseller_300_url(products[0]['query'], products[0]['min_cents'])}" target="_blank" rel="nofollow sponsored noopener" class="btn" style="padding: 11px 18px;">Check Compatible Best-Sellers on Amazon &rarr;</a>
            </div>
        </section>

        <h2 class="sec-title">Top-Ranked Amazon Best-Selling Power Stations & Bundles ($300+ Tier)</h2>
        <div class="grid">
            {cards_html}
        </div>

        <h2 class="sec-title">Other High-Demand Appliance Power Calculators</h2>
        <div class="rel-grid">
            {related_html}
        </div>
    </main>
    <footer>
        <p>As an Amazon Associate, this site earns from qualifying purchases. All hardware links filter automatically for high-capacity $300+ LiFePO4 systems sorted by Amazon Best-Seller popularity. Solar telemetry synced via Open-Meteo & NOAA API ({spec['updated_at']}).</p>
    </footer>
    <script>
        function recalcPower() {{
            const w = parseFloat(document.getElementById('runWatts').value) || {spec['run_w']};
            const h = parseFloat(document.getElementById('hoursInput').value) || {spec['default_hrs']};
            const d = parseFloat(document.getElementById('dutySelect').value) || 0.5;
            const grossWh = Math.ceil((w * h * d) / (0.85 * 0.90));
            document.getElementById('whResult').innerText = grossWh.toLocaleString() + ' Wh Minimum Capacity';
        }}
    </script>
</body>
</html>"""

    filepath = os.path.join(GUIDES_DIR, f"{spec['slug']}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)


def build_combo_pages(all_specs: list) -> list:
    """
    Membuat halaman kombinasi beban multi-alat (contoh: Refrigerator + CPAP, Sump Pump + Freezer)
    untuk menjaring kata kunci long-tail bernilai sangat tinggi ($1,000+ power stations).
    """
    os.makedirs(COMBOS_DIR, exist_ok=True)
    combo_urls = []
    subset = all_specs[:10]
    for i in range(len(subset)):
        for j in range(i + 1, len(subset)):
            a = subset[i]
            b = subset[j]
            combined_run = a["run_w"] + b["run_w"]
            combined_surge = max(a["surge_w"] + b["run_w"], b["surge_w"] + a["run_w"])
            combined_wh = a["gross_wh_required"] + b["gross_wh_required"]

            slug = f"solar-generator-to-run-{slugify(a['name'])}-and-{slugify(b['name'])}"
            page_url = f"{SITE_URL}/bundles/{slug}.html"

            amz_combo_url = make_amazon_bestseller_300_url(
                "2000Wh 3600Wh LiFePO4 solar generator portable power station home backup",
                75000
            )
            amz_solar_url = make_amazon_bestseller_300_url(
                "400W portable folding solar panel kit for power station",
                30000
            )

            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>What Size Solar Generator Runs {a['name']} + {b['name']} Together? ({combined_wh}Wh Guide)</title>
    <meta name="description" content="Combined wattage and LiFePO4 battery sizing to run both a {a['name']} and {b['name']} simultaneously: {combined_run}W continuous, {combined_surge}W peak surge, and {combined_wh}Wh storage.">
    <link rel="canonical" href="{page_url}">
    <style>
        :root {{ --bg: #090e17; --panel: #111827; --border: #1f2937; --text: #f8fafc; --muted: #94a3b8; --amber: #f59e0b; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.65; padding-bottom: 60px; }}
        header {{ background: #030712; border-bottom: 1px solid var(--border); padding: 18px 24px; }}
        .container {{ max-width: 980px; margin: 32px auto; padding: 0 20px; }}
        .box {{ background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 26px; margin-bottom: 24px; }}
        h1 {{ font-size: 1.75rem; margin-bottom: 12px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 20px; }}
        .btn {{ display: block; text-align: center; background: var(--amber); color: #030712; font-weight: 800; text-decoration: none; padding: 13px 16px; border-radius: 8px; margin-top: 16px; }}
        footer {{ text-align: center; color: var(--muted); font-size: 0.82rem; margin-top: 40px; }}
    </style>
</head>
<body>
    <header>
        <div style="max-width:980px;margin:0 auto;display:flex;justify-content:space-between;">
            <a href="{SITE_URL}/" style="color:#fff;font-weight:800;text-decoration:none;">Watt<span style="color:var(--amber);">Guard</span>300</a>
            <a href="{SITE_URL}/" style="color:var(--muted);text-decoration:none;">&larr; All Calculators</a>
        </div>
    </header>
    <main class="container">
        <div class="box">
            <h1>Combined Backup Sizing: {a['name']} + {b['name']}</h1>
            <p style="color:var(--muted);">Running both appliances simultaneously requires <strong>{combined_run}W continuous output</strong>, <strong>{combined_surge}W peak surge protection</strong>, and a minimum battery bank of <strong>{combined_wh}Wh</strong>.</p>
        </div>
        <div class="grid">
            <div class="box">
                <h2>1. Recommended 2,000Wh–3,600Wh LiFePO4 Station ($750+ Tier)</h2>
                <p style="color:var(--muted);margin-top:8px;">High-output pure sine wave station capable of handling the {combined_surge}W combined motor/compressor surge without voltage sag.</p>
                <a href="{amz_combo_url}" target="_blank" rel="nofollow sponsored noopener" class="btn">View Best-Selling 2000Wh+ Generators on Amazon &rarr;</a>
            </div>
            <div class="box">
                <h2>2. 400W Portable Bifacial Solar Array ($300+ Tier)</h2>
                <p style="color:var(--muted);margin-top:8px;">Replenish your battery bank daily during extended multi-day grid outages with weatherproof monocrystalline panels.</p>
                <a href="{amz_solar_url}" target="_blank" rel="nofollow sponsored noopener" class="btn">Check Best-Selling 400W Solar Panels on Amazon &rarr;</a>
            </div>
        </div>
    </main>
    <footer>
        <p>As an Amazon Associate, this site earns from qualifying purchases.</p>
    </footer>
</body>
</html>"""
            with open(os.path.join(COMBOS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
                f.write(html)
            combo_urls.append((f"{a['name']} + {b['name']}", slug, page_url))
    return combo_urls


def build_index_and_seo_files(db: dict, combo_links: list):
    os.makedirs(DOCS_DIR, exist_ok=True)
    specs_list = list(db.values())

    cards_html = ""
    for s in specs_list:
        cards_html += f"""
        <article class="item-card">
            <a href="{SITE_URL}/calculators/{s['slug']}.html" style="text-decoration:none;color:inherit;">
                <div class="item-top">
                    <span class="item-cat">{s['cat']}</span>
                    <span class="item-wh">{s['gross_wh_required']} Wh Min</span>
                </div>
                <h2>{s['name']}</h2>
                <p class="item-meta">Running: {s['run_w']}W &bull; Surge: {s['surge_w']}W &bull; Solar: {s['solar_input_w']}W</p>
                <span class="item-cta">Open Sizing Calculator & $300+ Best-Sellers &rarr;</span>
            </a>
        </article>
        """

    combos_html = ""
    for title, slug, _ in combo_links[:20]:
        combos_html += f'<a href="{SITE_URL}/bundles/{slug}.html" class="combo-pill">{title} &rarr;</a>\n'

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WattGuard300 - Solar Generator, LiFePO4 Battery & Home Backup Power Sizing Calculators</title>
    <meta name="description" content="Calculate exact Watt-Hour (Wh) battery capacity, inverter surge wattage, and solar panel array sizes for home backup appliances, RV air conditioners, sump pumps, and refrigerators.">
    <link rel="canonical" href="{SITE_URL}/">
    <style>
        :root {{ --bg: #090e17; --panel: #111827; --border: #1f2937; --text: #f8fafc; --muted: #94a3b8; --amber: #f59e0b; --green: #10b981; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        header {{ background: #030712; border-bottom: 1px solid var(--border); padding: 36px 20px; text-align: center; }}
        header h1 {{ font-size: 2.1rem; margin-bottom: 8px; }}
        header h1 span {{ color: var(--amber); }}
        header p {{ color: var(--muted); max-width: 720px; margin: 0 auto 20px; }}
        #searchBox {{ width: 100%; max-width: 560px; padding: 13px 16px; border-radius: 8px; border: 1px solid var(--border); background: #090e17; color: #fff; font-size: 1rem; }}
        .container {{ max-width: 1120px; margin: 36px auto; padding: 0 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 18px; }}
        .item-card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: transform 0.15s, border-color 0.15s; }}
        .item-card:hover {{ transform: translateY(-4px); border-color: var(--amber); }}
        .item-top {{ display: flex; justify-content: space-between; font-size: 0.76rem; margin-bottom: 8px; }}
        .item-cat {{ color: var(--amber); font-weight: 700; text-transform: uppercase; }}
        .item-wh {{ color: var(--green); font-weight: 700; }}
        .item-card h2 {{ font-size: 1.15rem; margin-bottom: 8px; color: #fff; }}
        .item-meta {{ font-size: 0.84rem; color: var(--muted); margin-bottom: 12px; }}
        .item-cta {{ font-size: 0.86rem; color: var(--amber); font-weight: 700; }}
        .combo-wrap {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
        .combo-pill {{ background: var(--panel); border: 1px solid var(--border); color: var(--text); text-decoration: none; padding: 8px 14px; border-radius: 8px; font-size: 0.84rem; }}
        .combo-pill:hover {{ border-color: var(--amber); }}
        footer {{ text-align: center; padding: 40px 20px; color: var(--muted); font-size: 0.82rem; border-top: 1px solid var(--border); margin-top: 60px; }}
    </style>
</head>
<body>
    <header>
        <h1>Watt<span>Guard</span>300 Solar & Backup Matrix</h1>
        <p>Automated Watt-Hour (Wh) Runtime Calculators, Surge Load Sizing & Best-Selling $300+ LiFePO4 Solar Generator Finder</p>
        <input type="text" id="searchBox" placeholder="Search appliance (e.g. Refrigerator, Sump Pump, CPAP, RV AC, Well Pump, Starlink)..." onkeyup="filterLoads()">
    </header>
    <main class="container">
        <div class="grid" id="loadsGrid">
            {cards_html}
        </div>
        <h2 style="font-size:1.4rem;margin:42px 0 12px;border-left:4px solid var(--amber);padding-left:12px;">Multi-Appliance Emergency Backup Sizing Guides</h2>
        <div class="combo-wrap">
            {combos_html}
        </div>
    </main>
    <footer>
        <p>As an Amazon Associate, this site earns from qualifying purchases. Automatically updated daily with Open-Meteo Solar Irradiance & NOAA Grid Alert telemetry.</p>
    </footer>
    <script>
        function filterLoads() {{
            const q = document.getElementById('searchBox').value.toLowerCase();
            document.querySelectorAll('.item-card').forEach(card => {{
                card.style.display = card.innerText.toLowerCase().includes(q) ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # Sitemap XML
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for s in specs_list:
        urls_xml += f"""  <url>
    <loc>{SITE_URL}/calculators/{s['slug']}.html</loc>
    <lastmod>{s.get('updated_at', today)}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    for _, _, full_combo_url in combo_links:
        urls_xml += f"""  <url>
    <loc>{full_combo_url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>\n"""

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls_xml}</urlset>"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def ping_indexnow(urls: list):
    if not urls or "username.github.io" in SITE_URL:
        return
    host = SITE_URL.replace("https://", "").replace("http://", "").split("/")[0]
    payload = {
        "host": host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls[:100]
    }
    try:
        r = requests.post(
            "https://api.indexnow.org/indexnow",
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=15
        )
        print(f"[INFO] IndexNow Ping HTTP Status: {r.status_code}")
    except Exception as e:
        print(f"[WARN] IndexNow Ping Error: {e}")


def main():
    db = load_db()
    telemetry = fetch_live_solar_and_grid_telemetry()
    new_urls = []
    added = 0

    for item in APPLIANCE_LOADS:
        key = item["name"]
        if key in db:
            # Perbarui telemetri surya & NOAA pada entri yang sudah ada
            db[key]["peak_sun_hours"] = telemetry["avg_peak_sun_hours"]
            db[key]["active_alerts"] = telemetry["active_us_weather_alerts"]
            continue
        if added >= 10:
            break
        spec = calculate_power_specs(item, telemetry)
        db[key] = spec
        new_urls.append(f"{SITE_URL}/calculators/{spec['slug']}.html")
        added += 1
        print(f"[OK] Halaman kalkulator dibuat: {key} ({spec['gross_wh_required']}Wh)")
        time.sleep(0.3)

    all_specs = list(db.values())
    for s in all_specs:
        build_appliance_page(s, all_specs)

    combo_links = build_combo_pages(all_specs)
    build_index_and_seo_files(db, combo_links)
    save_db(db)

    if new_urls:
        new_urls.append(f"{SITE_URL}/")
        for _, _, c_url in combo_links[:25]:
            new_urls.append(c_url)
        ping_indexnow(new_urls)

    print(f"[DONE] Total halaman kalkulator: {len(all_specs)} | Halaman kombinasi: {len(combo_links)}")


if __name__ == "__main__":
    main()
