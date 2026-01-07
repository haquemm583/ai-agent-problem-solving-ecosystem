# 🚀 3D Mission Control Dashboard - User Guide

## Overview

The MA-GET dashboard has been upgraded with a stunning **3D Mission Control** view powered by PyDeck, transforming your logistics network visualization into an immersive experience.

## New Features

### 1. 3D Network Visualization 🗺️

The new 3D map replaces the flat 2D Plotly graph with three dynamic layers:

#### **Layer 1: Inventory Columns** 📦
- **Visual**: 3D vertical columns at each city location
- **Height**: Represents current inventory level (taller = more inventory)
- **Color Coding**:
  - 🟢 **Green**: Low usage (<30% capacity)
  - 🟡 **Yellow**: Medium usage (30-70% capacity)
  - 🔴 **Red**: High usage (>70% capacity) - Action needed!
- **Purpose**: Instantly see which cities need restocking

#### **Layer 2: Route Arcs** 🛣️
- **Visual**: Curved arcs connecting cities
- **Thickness**: Represents fuel cost multiplier (thicker = more expensive)
- **Color Gradient**: 
  - Green at origin city
  - Red at destination city
  - Shows flow direction at a glance
- **Purpose**: Visualize route costs and connections

#### **Layer 3: Active Shipments** 🚚
- **Visual**: Yellow scatter points
- **Location**: Cities with high demand
- **Purpose**: Track areas with active shipping activity
- **Future Enhancement**: Will show real-time truck positions

### 2. Interactive Camera Controls 🎮

Take full control of your viewing angle:

- **🔄 Reset View**: Instantly return to default Texas view
- **⬆️ Tilt (Pitch)**: Angle the camera from 0° (top-down) to 85° (almost horizontal)
  - Perfect for seeing the height of inventory columns
- **🔄 Rotate (Bearing)**: Spin the map 360° around
  - Find the best angle to analyze your network
- **🔍 Zoom**: Zoom from 4.0 (wide view) to 8.0 (street level)
  - Get close to examine specific cities

**Pro Tip**: Set pitch to 45-60° and rotate slowly to see inventory levels in 3D!

### 3. Live Feed Panel 📡

#### **Natural Language News Ticker**

Gone are the raw JSON logs! Now you get human-readable breaking news:

**Before** (Raw JSON):
```json
{"event": "WEATHER", "type": "STORM", "loc": "Houston"}
```

**After** (Natural Language):
```
🚨 BREAKING: Severe Storm in Houston! Shipping delays expected.
```

#### Event Types Translated:

- **Weather Events**:
  - ☀️ Clear skies announcements
  - 🌧️ Rain alerts
  - 🚨 Storm warnings
  - 🌫️ Fog advisories

- **Route Updates**:
  - 🚧 Route closures
  - ✅ Route reopenings

- **Negotiations**:
  - 💼 Deal in progress
  - 🎉 Deal closed (with price)
  - ❌ Deal failed
  - ⏰ Deal expired

- **Market Activity**:
  - 💰 New offers
  - 🌍 Market updates

Each news item is timestamped and styled in an attractive card format, making it easy to follow the action!

## How to Use

### Installation

1. **Update dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   This will install `pydeck>=0.8.0` along with other required packages.

### Running the Dashboard

```bash
streamlit run dashboard.py
```

### Navigation

1. **Select the "🗺️ Network View" tab** (should be the first tab)

2. **Explore the 3D Map**:
   - The map automatically renders on the left (2/3 of the screen)
   - Camera controls are on the right (1/3 of the screen)

3. **Adjust Your View**:
   - Use sliders to tilt, rotate, and zoom
   - Click "🔄 Reset View" to return to default

4. **Read the Legend**:
   - Color meanings for inventory
   - Route visualization explained
   - Shipment indicators

5. **Monitor the Live Feed**:
   - Scroll through real-time news tickers
   - Watch for breaking events
   - No filtering needed - all important events shown automatically

### Tooltip Interactions

**Hover over elements** to see detailed information:
- **Cities**: Name, inventory, capacity
- **Routes**: Cities connected, distance, fuel cost, weather
- **Shipments**: City name, demand level

## Technical Details

### Files Modified/Created

1. **`viz_components.py`** (NEW):
   - Core 3D visualization logic
   - Layer builders for inventory, routes, and shipments
   - Color mapping functions
   - View state management

2. **`dashboard.py`** (UPDATED):
   - Imports PyDeck and viz_components
   - Camera control state management
   - Live Feed display function
   - Event-to-news converter
   - Integrated 3D map into Network View tab

3. **`requirements.txt`** (UPDATED):
   - Added `pydeck>=0.8.0`

### Architecture

```
dashboard.py
    ↓ imports
viz_components.py
    ↓ uses
world.py (WorldState)
    ↓ contains
schema.py (CityNode, RouteEdge)
```

### PyDeck Layers Used

- **ColumnLayer**: 3D extruded columns for inventory
- **ArcLayer**: Curved lines for routes
- **ScatterplotLayer**: Points for shipments

## Customization

### Change Default View

Edit in `viz_components.py`:
```python
def get_default_texas_view() -> pdk.ViewState:
    return pdk.ViewState(
        latitude=29.5,      # Center latitude
        longitude=-96.5,    # Center longitude
        zoom=5.5,           # Zoom level
        pitch=45,           # Tilt angle
        bearing=0,          # Rotation
    )
```

### Adjust Inventory Column Height

In `build_inventory_layer()`:
```python
'elevation': current_inv * 100,  # Change multiplier (100)
```

### Modify Route Thickness

In `get_route_width()`:
```python
return max(2, min(20, fuel_multiplier * 5))  # Adjust multiplier
```

### Add More News Types

In `convert_event_to_news()`, add new event type handlers:
```python
elif event.event_type == EventType.NEW_TYPE:
    return f"🎯 Your custom message here"
```

## Troubleshooting

### Map Not Rendering
- **Check PyDeck installation**: `pip list | grep pydeck`
- **Verify Mapbox token**: PyDeck uses Mapbox by default
- **Browser compatibility**: Use Chrome/Firefox/Edge (latest versions)

### Camera Controls Not Working
- **Clear cache**: Streamlit menu → Clear cache
- **Restart server**: Ctrl+C and run `streamlit run dashboard.py` again

### Live Feed Empty
- **Run simulation**: Events only appear during active simulation
- **Check event log file**: `.maget_events.json` should exist
- **Generate activity**: Run negotiations or trigger weather events

## Future Enhancements

Potential additions to consider:

1. **Real-time Truck Animation**: Animate shipments moving along routes
2. **Time-lapse Mode**: Replay historical data with animation
3. **Heat Maps**: Show demand/supply heat over time
4. **Cluster View**: Group nearby shipments
5. **VR Mode**: Export to VR-compatible format
6. **Screenshot Export**: Save specific views as images

## Performance Notes

- **Large datasets**: PyDeck handles thousands of points efficiently
- **Browser impact**: 3D rendering uses GPU acceleration
- **Mobile**: Works but camera controls are limited on touchscreens

## Credits

Built with:
- **PyDeck**: Visualization framework
- **Streamlit**: Dashboard framework
- **Mapbox**: Base map provider
- **MA-GET**: Multi-Agent Economic Twin platform

---

**Enjoy your new Mission Control! 🚀**

For questions or issues, refer to the main [README.md](README.md).
