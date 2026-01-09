import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Box } from '@react-three/drei';
import * as THREE from 'three';
import axios from 'axios';
import './App.css';

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

interface City {
  name: string;
  latitude: number;
  longitude: number;
  inventory: number;
  capacity: number;
  demand_rate: number;
}

interface Route {
  source: string;
  target: string;
  distance: number;
  weather: string;
  fuel_multiplier: number;
  is_open: boolean;
}

interface SimulationState {
  running: boolean;
  tick_count: number;
  total_orders: number;
  active_routes: number;
}

interface WorldData {
  cities: City[];
  routes: Route[];
  simulation: SimulationState;
}

// =============================================================================
// 3D COMPONENTS
// =============================================================================

// Building component - represents a warehouse
const Building: React.FC<{ 
  position: [number, number, number]; 
  height: number; 
  color: string;
  label: string;
}> = ({ position, height, color, label }) => {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (meshRef.current) {
      // Subtle breathing animation
      const scale = 1 + Math.sin(Date.now() * 0.001) * 0.02;
      meshRef.current.scale.set(1, scale, 1);
    }
  });

  return (
    <group position={position}>
      {/* Building structure */}
      <Box args={[0.5, height, 0.5]} position={[0, height / 2, 0]} ref={meshRef}>
        <meshStandardMaterial color={color} metalness={0.3} roughness={0.7} />
      </Box>
      {/* Building base */}
      <Box args={[0.6, 0.1, 0.6]} position={[0, 0, 0]}>
        <meshStandardMaterial color="#444444" />
      </Box>
      {/* City label */}
      <Text
        position={[0, height + 0.5, 0]}
        fontSize={0.3}
        color="white"
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </Text>
    </group>
  );
};

// Truck component - animated delivery trucks
const Truck: React.FC<{
  start: [number, number, number];
  end: [number, number, number];
  progress: number;
}> = ({ start, end, progress }) => {
  const position: [number, number, number] = [
    start[0] + (end[0] - start[0]) * progress,
    0.2,
    start[2] + (end[2] - start[2]) * progress,
  ];

  return (
    <group position={position}>
      {/* Truck body */}
      <Box args={[0.3, 0.2, 0.15]}>
        <meshStandardMaterial color="#ff6b35" />
      </Box>
      {/* Truck cab */}
      <Box args={[0.15, 0.15, 0.15]} position={[0.15, 0.05, 0]}>
        <meshStandardMaterial color="#c44536" />
      </Box>
    </group>
  );
};

// Road component - connects cities
const Road: React.FC<{
  start: [number, number, number];
  end: [number, number, number];
  color: string;
}> = ({ start, end, color }) => {
  const points = [new THREE.Vector3(...start), new THREE.Vector3(...end)];
  
  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={points.length}
          array={new Float32Array(points.flatMap((p) => [p.x, p.y, p.z]))}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial attach="material" color={color} linewidth={2} />
    </line>
  );
};

// Main 3D Scene
const Scene: React.FC<{ worldData: WorldData | null }> = ({ worldData }) => {
  const [trucks, setTrucks] = useState<Array<{ start: [number, number, number]; end: [number, number, number]; progress: number }>>([]);

  // Convert lat/lon to 3D coordinates
  const latLonTo3D = (lat: number, lon: number): [number, number, number] => {
    const centerLat = 30.5;
    const centerLon = -97.5;
    const scale = 20;

    const x = (lon - centerLon) * scale;
    const z = (lat - centerLat) * scale;
    return [x, 0, z];
  };

  // Get building height based on inventory
  const getBuildingHeight = (inventory: number, capacity: number): number => {
    const percentage = inventory / capacity;
    return 0.5 + percentage * 2;
  };

  // Get building color based on capacity
  const getBuildingColor = (inventory: number, capacity: number): string => {
    const percentage = inventory / capacity;
    if (percentage < 0.3) return '#44ff44';
    if (percentage < 0.7) return '#ffaa00';
    return '#ff4444';
  };

  // Generate random trucks for animation
  useEffect(() => {
    if (worldData && worldData.simulation.running) {
      const interval = setInterval(() => {
        const newTrucks = worldData.routes
          .filter(route => route.is_open && Math.random() > 0.7)
          .map(route => {
            const sourceCity = worldData.cities.find(c => c.name === route.source);
            const targetCity = worldData.cities.find(c => c.name === route.target);
            if (sourceCity && targetCity) {
              return {
                start: latLonTo3D(sourceCity.latitude, sourceCity.longitude),
                end: latLonTo3D(targetCity.latitude, targetCity.longitude),
                progress: Math.random(),
              };
            }
            return null;
          })
          .filter(t => t !== null) as Array<{ start: [number, number, number]; end: [number, number, number]; progress: number }>;

        setTrucks(newTrucks);
      }, 3000);

      return () => clearInterval(interval);
    }
  }, [worldData]);

  if (!worldData) {
    return (
      <Text position={[0, 0, 0]} fontSize={0.5} color="white">
        Loading...
      </Text>
    );
  }

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} />
      <pointLight position={[-10, 10, -5]} intensity={0.5} />

      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <planeGeometry args={[50, 50]} />
        <meshStandardMaterial color="#1a1a2e" />
      </mesh>

      {/* Cities as buildings */}
      {worldData.cities.map((city) => {
        const pos = latLonTo3D(city.latitude, city.longitude);
        const height = getBuildingHeight(city.inventory, city.capacity);
        const color = getBuildingColor(city.inventory, city.capacity);
        
        return (
          <Building
            key={city.name}
            position={pos}
            height={height}
            color={color}
            label={city.name}
          />
        );
      })}

      {/* Roads between cities */}
      {worldData.routes.map((route, index) => {
        const sourceCity = worldData.cities.find(c => c.name === route.source);
        const targetCity = worldData.cities.find(c => c.name === route.target);
        
        if (sourceCity && targetCity) {
          const start = latLonTo3D(sourceCity.latitude, sourceCity.longitude);
          const end = latLonTo3D(targetCity.latitude, targetCity.longitude);
          const color = route.is_open ? '#00ff88' : '#ff0000';
          
          return <Road key={index} start={start} end={end} color={color} />;
        }
        return null;
      })}

      {/* Animated trucks */}
      {trucks.map((truck, index) => (
        <Truck key={index} start={truck.start} end={truck.end} progress={truck.progress} />
      ))}

      {/* Camera controls */}
      <OrbitControls
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={5}
        maxDistance={30}
      />
    </>
  );
};

// =============================================================================
// MAIN APP COMPONENT
// =============================================================================

const App: React.FC = () => {
  const [worldData, setWorldData] = useState<WorldData | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const API_BASE = 'http://localhost:8000';

  // Fetch world state
  const fetchWorldState = async () => {
    try {
      const response = await axios.get<WorldData>(`${API_BASE}/api/world`);
      setWorldData(response.data);
      setIsRunning(response.data.simulation.running);
    } catch (error) {
      console.error('Error fetching world state:', error);
    }
  };

  // Start simulation
  const handleStart = async () => {
    try {
      await axios.post(`${API_BASE}/api/simulation/start`);
      setIsRunning(true);
    } catch (error) {
      console.error('Error starting simulation:', error);
    }
  };

  // Stop simulation
  const handleStop = async () => {
    try {
      await axios.post(`${API_BASE}/api/simulation/stop`);
      setIsRunning(false);
    } catch (error) {
      console.error('Error stopping simulation:', error);
    }
  };

  // Simulation tick
  const simulationTick = async () => {
    if (isRunning) {
      try {
        await axios.post(`${API_BASE}/api/simulation/tick`);
        await fetchWorldState();
      } catch (error) {
        console.error('Error during simulation tick:', error);
      }
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchWorldState();
  }, []);

  // Auto-update loop
  useEffect(() => {
    const interval = setInterval(() => {
      if (isRunning) {
        simulationTick();
      } else {
        fetchWorldState();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [isRunning]);

  return (
    <div className="App">
      {/* Header */}
      <div className="header">
        <h1>🌍 3D Logistics Simulation</h1>
        <div className="status">
          {isRunning ? '🟢 RUNNING' : '🔴 STOPPED'}
        </div>
      </div>

      {/* Control Panel */}
      <div className="controls">
        <button
          className={isRunning ? 'stop-btn' : 'start-btn'}
          onClick={isRunning ? handleStop : handleStart}
        >
          {isRunning ? '⏸ STOP' : '▶ START'}
        </button>
      </div>

      {/* Stats Panel */}
      {worldData && (
        <div className="stats">
          <div className="stat-item">
            <span className="stat-label">Ticks:</span>
            <span className="stat-value">{worldData.simulation.tick_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Orders:</span>
            <span className="stat-value">{worldData.simulation.total_orders}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Routes:</span>
            <span className="stat-value">{worldData.simulation.active_routes}</span>
          </div>
        </div>
      )}

      {/* 3D Canvas */}
      <div className="canvas-container">
        <Canvas
          camera={{ position: [0, 15, 15], fov: 60 }}
          shadows
        >
          <Scene worldData={worldData} />
        </Canvas>
      </div>
    </div>
  );
};

export default App;
