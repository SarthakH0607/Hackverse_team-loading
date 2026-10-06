# Map Popup Specifications & Field Mapping

This reference document defines the exact fields, formatting rules, and labels to render in each map popup layer on the frontend map interface.

---

## 1. Prioritized Villages Layer (`villages_ranked.geojson`)

### Fields to Show:
- **Rank**: `#{{ rank }}` (Priority rank from 1 to N)
- **Name**: `{{ name }}` (Settlement name)
- **Population**: `{{ population }}` (Estimated baseline population)
- **Confidence**: `{{ confidence }}` (Model confidence score, 2 decimals, e.g. `0.72`)
- **Reason**: `{{ reason }}` (Diagnostic plain-language explanation)

### Real Example Feature:
```json
{
  "type": "Feature",
  "properties": {
    "rank": 1,
    "name": "Rangpo",
    "population": 5000,
    "score": 1094.81,
    "reason": "~5000 people (est.), 19% of area changed, some access road blocked, nearest unaffected hospital 0 km away",
    "confidence": 0.72
  },
  "geometry": {
    "type": "Point",
    "coordinates": [
      88.5303403,
      27.1744361
    ]
  }
}
```

---

## 2. Safe Evacuation Zones Layer (`safe_zones.geojson`)

### Fields to Show:
- **Name**: `{{ name }}` (Facility / safe zone name)
- **Type**: `{{ type }}` (`hospital`, `shelter`, or `water`)
- **One-Line Label**:
  - For `hospital`: `Verified Healthcare Hub (Outside active hazard zone, slope < 15°)`
  - For `shelter`: `Evacuation Assembly Shelter (Slope < 15°, > 200m from rivers)`
  - For `water`: `Clean Water Point (> 200m from river contamination)`

### Real Example Feature:
```json
{
  "type": "Feature",
  "properties": {
    "name": "Government General Hospital Blood Bank - Namchi",
    "type": "hospital",
    "lat": 27.165504,
    "lon": 88.360583
  },
  "geometry": {
    "type": "Point",
    "coordinates": [
      88.360583,
      27.1655039
    ]
  }
}
```

---

## 3. Weather & Slope Risk Alerts Layer (`risk_alerts.geojson`)

### Fields to Show:
- **Risk**: `{{ risk }}` (`Low`, `Med`, or `High`)
- **Rainfall (3-Day)**: `{{ rain_mm }} mm` (Open-Meteo forecast total accumulation)
- **Note**: `{{ note }}` (`Risk alert, not a prediction. Glacial lake outbursts are not rain-driven and are not covered.`)

### Real Example Feature:
```json
{
  "type": "Feature",
  "properties": {
    "zone": "Zone 1",
    "risk": "High",
    "rain_mm": 10.3,
    "slope_class": "High",
    "note": "Risk alert, not a prediction. Glacial lake outbursts are not rain-driven and are not covered."
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [
          88.3,
          27.55
        ],
        [
          88.45,
          27.55
        ],
        [
          88.45,
          27.75
        ],
        [
          88.3,
          27.75
        ],
        [
          88.3,
          27.55
        ]
      ]
    ]
  }
}
```

---

## 4. Incident Report Path

- **Static HTML Incident Report**: `frontend/public/data/incident_report.html`
- **Report Route / Direct Link**: `/data/incident_report.html`
