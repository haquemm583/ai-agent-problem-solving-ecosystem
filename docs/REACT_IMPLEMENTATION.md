# React + Three.js Implementation Guide

## Overview

The MA-GET simulation has been migrated from Streamlit to a modern **React + Three.js** stack for better 3D visualization and user experience.

## Architecture

### Frontend (React + TypeScript + Three.js)
- **React 18**: Component-based UI framework
- **TypeScript**: Type-safe development
- **Three.js**: Low-level 3D graphics library
- **React Three Fiber**: React renderer for Three.js
- **@react-three/drei**: Helpful components and hooks

### Backend (FastAPI + Python)
- **FastAPI**: Modern async Python web framework
- **Uvicorn**: ASGI server for FastAPI
- **CORS middleware**: Allows frontend to communicate with backend
- **RESTful API**: Clean separation between frontend and backend

## Key Features

### 3D Visualization

#### Buildings (Warehouses)
- Represented as 3D box geometries
- **Height**: Dynamically calculated from inventory/capacity ratio
  - Min height: 0.5 units (empty)
  - Max height: 2.5 units (full)
- **Color coding**:
  - 🟢 Green: < 30% capacity
  - 🟡 Yellow: 30-70% capacity
  - 🔴 Red: > 70% capacity
- **Animation**: Subtle breathing effect (scale pulsing)
- **Labels**: City names displayed above buildings

#### Trucks (Delivery Vehicles)
- Animated 3D models moving along routes
- **Components**:
  - Main body (larger box)
  - Cab (smaller box at front)
- **Movement**: Linear interpolation between source and destination
- **Spawning**: Random generation based on active routes
- **Colors**: Orange (#ff6b35) for visibility

#### Roads (Route Networks)
- Lines connecting cities
- **Color**:
  - 🟢 Green (#00ff88): Open routes
  - 🔴 Red (#ff0000): Closed/blocked routes
- **Rendering**: Using Three.js Line geometry

#### Environment
- **Ground plane**: Dark background (50x50 units)
- **Lighting**:
  - Ambient light: Overall scene illumination
  - Directional light: Main light with shadows
  - Point light: Additional highlights

### Interactive Controls
- **Orbit**: Drag to rotate camera around scene
- **Zoom**: Mouse wheel to zoom in/out
- **Pan**: Right-click drag to move camera
- **Limits**:
  - Min distance: 5 units
  - Max distance: 30 units

### Single Button Interface
- **START button** (green): Begins simulation
- **STOP button** (red): Pauses simulation
- Large, centered, easy to use
- Smooth hover animations

### Real-time Stats
- **Ticks**: Number of simulation updates
- **Orders**: Total orders generated
- **Routes**: Number of active (open) routes
- Displayed in top-right corner
- Monospace font for readability

## API Endpoints

### GET `/`
Health check endpoint
```json
{
  "status": "online",
  "message": "MA-GET Simulation API"
}
```

### GET `/api/world`
Get complete world state
```json
{
  "cities": [
    {
      "name": "Houston",
      "latitude": 29.7604,
      "longitude": -95.3698,
      "inventory": 2000,
      "capacity": 5000,
      "demand_rate": 1.5
    },
    ...
  ],
  "routes": [
    {
      "source": "Houston",
      "target": "Dallas",
      "distance": 239.0,
      "weather": "CLEAR",
      "fuel_multiplier": 1.0,
      "is_open": true
    },
    ...
  ],
  "simulation": {
    "running": false,
    "tick_count": 0,
    "total_orders": 0,
    "active_routes": 7
  }
}
```

### POST `/api/simulation/start`
Start the simulation
```json
{
  "status": "started",
  "running": true
}
```

### POST `/api/simulation/stop`
Stop the simulation
```json
{
  "status": "stopped",
  "running": false
}
```

### POST `/api/simulation/tick`
Advance simulation by one tick (called automatically by frontend)
```json
{
  "tick": 42,
  "running": true
}
```

## Data Flow

1. **Frontend loads** → Fetches initial world state from `/api/world`
2. **User clicks START** → POST to `/api/simulation/start`
3. **Auto-update loop begins** (every 2 seconds):
   - POST to `/api/simulation/tick` (advances simulation)
   - GET `/api/world` (fetch updated state)
   - Update React state
   - Re-render 3D scene
4. **User clicks STOP** → POST to `/api/simulation/stop`

## Coordinate System

### Geographic to 3D Conversion
```typescript
const latLonTo3D = (lat: number, lon: number): [number, number, number] => {
  const centerLat = 30.5;   // Center on Texas
  const centerLon = -97.5;
  const scale = 20;         // Scale for visibility

  const x = (lon - centerLon) * scale;
  const z = (lat - centerLat) * scale;
  return [x, 0, z];
};
```

This projects Texas cities onto a 3D plane:
- **X axis**: West (-) to East (+)
- **Y axis**: Height (inventory, trucks at 0.2)
- **Z axis**: South (-) to North (+)

## Performance Optimizations

1. **React Three Fiber**: Efficient React reconciliation for 3D objects
2. **useFrame hook**: Smooth 60fps animations
3. **Conditional rendering**: Only render trucks when simulation running
4. **Memoization**: React state updates trigger targeted re-renders
5. **API polling**: 2-second interval balances responsiveness and load

## Development

### File Structure
```
frontend/
├── public/                 # Static assets
├── src/
│   ├── App.tsx            # Main component with 3D scene
│   ├── App.css            # Styling
│   ├── index.tsx          # Entry point
│   └── ...
├── package.json           # Dependencies
└── tsconfig.json          # TypeScript config
```

### Key Dependencies
```json
{
  "three": "^0.160.0",
  "@react-three/fiber": "^8.15.0",
  "@react-three/drei": "^9.90.0",
  "axios": "^1.6.0"
}
```

### Running Locally
```bash
# Terminal 1: Backend
python backend.py

# Terminal 2: Frontend
cd frontend
npm start
```

Frontend runs on `http://localhost:3000`  
Backend API on `http://localhost:8000`

## Customization

### Change Colors
Edit `App.tsx`:
```typescript
const getBuildingColor = (inventory: number, capacity: number): string => {
  const percentage = inventory / capacity;
  if (percentage < 0.3) return '#44ff44'; // Change green
  if (percentage < 0.7) return '#ffaa00'; // Change yellow
  return '#ff4444'; // Change red
};
```

### Adjust Camera
Edit `App.tsx` in the `<Canvas>` component:
```typescript
<Canvas
  camera={{ position: [0, 15, 15], fov: 60 }}  // Change position/FOV
  shadows
>
```

### Modify Truck Appearance
Edit the `Truck` component in `App.tsx`:
```typescript
<Box args={[0.3, 0.2, 0.15]}>  // Change size
  <meshStandardMaterial color="#ff6b35" />  // Change color
</Box>
```

### Change Update Frequency
Edit the `useEffect` hook in `App`:
```typescript
const interval = setInterval(() => {
  // ...
}, 2000); // Change from 2000ms (2 seconds) to desired interval
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 is available: `lsof -i :8000`

### Frontend won't start
- Check Node version: `node --version` (need 16+)
- Install dependencies: `cd frontend && npm install`
- Clear cache: `rm -rf node_modules package-lock.json && npm install`

### CORS errors
- Ensure backend is running on `http://localhost:8000`
- Check CORS middleware in `backend.py`
- Frontend must be on `http://localhost:3000`

### 3D scene not rendering
- Check browser console for WebGL errors
- Ensure browser supports WebGL 2.0
- Try different browser (Chrome recommended)

## Future Enhancements

1. **Better 3D models**: Import GLB/GLTF models for trucks and buildings
2. **Animated movement**: Smooth truck interpolation along routes
3. **Weather effects**: Visual indicators (rain, storm animations)
4. **Sound effects**: Audio feedback for events
5. **Mobile support**: Touch controls for mobile devices
6. **VR mode**: WebXR support for VR headsets
7. **Time controls**: Speed up/slow down simulation
8. **Replay mode**: Save and replay historical data

## Conclusion

The React + Three.js implementation provides:
- ✅ Modern, responsive UI
- ✅ Stunning 3D graphics
- ✅ Smooth animations
- ✅ Type-safe development
- ✅ Clean API separation
- ✅ Easy to extend and customize

This is a significant upgrade from the Streamlit version, offering better performance, more flexibility, and a professional user experience.
