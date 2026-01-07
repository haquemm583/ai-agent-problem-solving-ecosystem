# 🚀 Quick Start: 3D Mission Control

## Installation

### 1. Install New Dependencies

```bash
pip install pydeck>=0.8.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
python -c "import pydeck; print(f'PyDeck version: {pydeck.__version__}')"
```

Expected output: `PyDeck version: 0.8.x` or higher

## Running the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

## First Time Setup

1. **Navigate to "🗺️ Network View" tab** (first tab)
2. **You should see**:
   - 3D map with colored columns (cities)
   - Green-to-red arcs (routes)
   - Camera control panel on the right
   - Live Feed panel at bottom

3. **Test Camera Controls**:
   - Move the "Tilt" slider to see columns rise
   - Rotate the map with "Bearing" slider
   - Zoom in/out to explore
   - Click "Reset View" to return to default

## Testing Features

### Test 1: View 3D Inventory

1. Look at the colored columns on the map
2. Green = low inventory, Red = high inventory
3. Hover over a column to see city details

### Test 2: Camera Controls

1. Set Tilt to 60° (to see column heights better)
2. Set Bearing to 45° (rotate the map)
3. Set Zoom to 6.0 (closer view)
4. Click "Reset View" to go back

### Test 3: Live Feed

1. Scroll down to the Live Feed panel
2. You should see styled news cards
3. Run a simulation to generate events:
   - Use sidebar controls
   - Events will appear as natural language

### Test 4: Route Visualization

1. Look at the arcs connecting cities
2. Thicker arcs = more expensive routes
3. Hover to see distance, fuel cost, weather

## Troubleshooting

### Issue: Map Not Showing

**Solution 1**: Check browser console for errors
- Press F12 in browser
- Look for JavaScript errors
- Try Chrome/Firefox (latest version)

**Solution 2**: Verify PyDeck installation
```bash
pip uninstall pydeck
pip install pydeck>=0.8.0
```

**Solution 3**: Clear Streamlit cache
- Click "☰" menu in dashboard
- Select "Clear cache"
- Refresh page

### Issue: Camera Controls Not Working

**Solution**: Restart Streamlit
```bash
# Press Ctrl+C in terminal
streamlit run dashboard.py
```

### Issue: No Events in Live Feed

**Solution**: Generate simulation activity
1. Use sidebar to start simulation
2. Run negotiations
3. Trigger weather changes
4. Events will populate automatically

### Issue: ImportError for pydeck

**Error Message**: `ModuleNotFoundError: No module named 'pydeck'`

**Solution**:
```bash
pip install pydeck
```

If using virtual environment:
```bash
# Activate venv first
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Then install
pip install pydeck
```

## Performance Tips

### For Smooth 3D Rendering:

1. **Use a modern browser**:
   - Chrome 90+
   - Firefox 88+
   - Edge 90+

2. **Enable GPU acceleration**:
   - Chrome: `chrome://settings/system`
   - Check "Use hardware acceleration when available"

3. **Close other browser tabs** to free up GPU memory

4. **Reduce data if slow**:
   - Lower number of events in Live Feed
   - Adjust camera view to focus on specific area

## Next Steps

Once everything is working:

1. **Explore the Dashboard**:
   - Try all tabs
   - Run negotiations
   - Watch the 3D visualization update

2. **Read Full Guide**:
   - [3D_DASHBOARD_GUIDE.md](3D_DASHBOARD_GUIDE.md) - Complete feature overview
   - [3D_IMPLEMENTATION_SUMMARY.md](3D_IMPLEMENTATION_SUMMARY.md) - Technical details

3. **Customize**:
   - Edit `viz_components.py` to change colors
   - Adjust camera defaults
   - Add new event types to Live Feed

## Quick Feature Reference

| Feature | Location | Key Controls |
|---------|----------|--------------|
| 3D Map | Network View Tab → Left side | Hover to see tooltips |
| Camera Controls | Network View Tab → Right panel | Sliders for tilt/rotate/zoom |
| Live Feed | Network View Tab → Bottom right | Auto-updates with news |
| City Inventory | Network View Tab → Bottom left | Colored progress bars |
| Route Table | Network View Tab → Below map | Sortable data table |

## Common Questions

**Q: Can I export the 3D view?**
A: Screenshot with your browser (Ctrl+Shift+S in Firefox, or browser extensions)

**Q: Can I change the map style?**
A: Yes, edit `render_3d_map()` in viz_components.py:
```python
map_style="mapbox://styles/mapbox/dark-v10"  # Change this
```

**Q: How do I see real-time updates?**
A: Run the simulation from the sidebar - the map auto-refreshes

**Q: Can I add more cities?**
A: Yes, edit `world.py` to add cities to `TEXAS_CITIES`

**Q: Why are some routes missing?**
A: Closed routes (due to weather) are filtered out. Check Route Status table.

## Support

If you encounter issues:

1. Check the error message carefully
2. Verify all dependencies installed
3. Review the troubleshooting section above
4. Check [3D_DASHBOARD_GUIDE.md](3D_DASHBOARD_GUIDE.md) for detailed help

---

**Happy visualizing! 🎉**

Your 3D Mission Control is ready to explore the MA-GET logistics network!
