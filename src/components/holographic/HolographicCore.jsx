import React, { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import * as THREE from 'three';

// ── Fresnel holographic shader material ──
const HolographicMaterial = ({ baseColor = '#16d9ff', glowColor = '#7af9ff', intensity = 0.6 }) => {
  const materialRef = useRef();

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime;
    }
  });

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uBaseColor: { value: new THREE.Color(baseColor) },
    uGlowColor: { value: new THREE.Color(glowColor) },
    uIntensity: { value: intensity },
  }), [baseColor, glowColor, intensity]);

  return (
    <shaderMaterial
      ref={materialRef}
      uniforms={uniforms}
      transparent
      side={THREE.DoubleSide}
      blending={THREE.AdditiveBlending}
      vertexShader={`
        varying vec3 vNormal;
        varying vec3 vViewDir;
        varying vec2 vUv;
        uniform float uTime;

        void main() {
          vNormal = normalize(normalMatrix * normal);
          vec4 worldPos = modelMatrix * vec4(position, 1.0);
          vViewDir = normalize(cameraPosition - worldPos.xyz);
          vUv = uv;
          // Subtle vertex displacement for "breathing" effect
          vec3 displaced = position + normal * sin(position.y * 3.0 + uTime * 0.8) * 0.008;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
        }
      `}
      fragmentShader={`
        uniform vec3 uBaseColor;
        uniform vec3 uGlowColor;
        uniform float uIntensity;
        uniform float uTime;
        varying vec3 vNormal;
        varying vec3 vViewDir;
        varying vec2 vUv;

        void main() {
          float fresnel = 1.0 - max(dot(vNormal, vViewDir), 0.0);
          fresnel = pow(fresnel, 2.8);

          // Scanline effect
          float scan = sin(vUv.y * 120.0 + uTime * 2.0) * 0.5 + 0.5;
          scan = smoothstep(0.3, 0.7, scan);

          // Glitch lines
          float glitchLine = sin(vUv.y * 240.0 + uTime * 5.0) * 0.5 + 0.5;
          float glitch = step(0.995, glitchLine) * 0.3;

          // Color composition
          vec3 color = mix(uBaseColor, uGlowColor, fresnel * 0.7);
          color += vec3(0.2, 0.6, 1.0) * fresnel * uIntensity * 0.5;
          color += uGlowColor * scan * 0.08;
          color += vec3(1.0, 1.0, 1.0) * glitch;

          float alpha = fresnel * 0.55 + 0.12 + scan * 0.05;
          alpha *= uIntensity;

          gl_FragColor = vec4(color, alpha);
        }
      `}
    />
  );
};

// ── Fresnel glowing ring ──
const FresnelRing = ({ radius, tube, color, speed, tilt, opacity = 0.35, scanlines = false }) => {
  const ref = useRef();
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.z += delta * speed;
  });

  return (
    <mesh ref={ref} rotation={[tilt, 0, 0]}>
      <torusGeometry args={[radius, tube, 16, 180]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} />
    </mesh>
  );
};

// ── Data arc with glow ──
const DataArc = ({ radius, start, length, color, speed, y = 0, thickness = 1 }) => {
  const ref = useRef();
  const geometry = useMemo(() => {
    const curve = new THREE.EllipseCurve(0, 0, radius, radius, start, start + length, false, 0);
    const points = curve.getPoints(60).map((point) => new THREE.Vector3(point.x, y, point.y));
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [length, radius, start, y]);

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * speed;
  });

  return (
    <line ref={ref} geometry={geometry}>
      <lineBasicMaterial color={color} transparent opacity={0.85} linewidth={thickness} />
    </line>
  );
};

// ── Audio-reactive particle field ──
const AudioReactiveParticles = ({ count = 350, audioAmp = 0 }) => {
  const pointsRef = useRef();
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      const radius = 2.0 + ((i % 31) / 31) * 3.2;
      const angle = i * 2.399963;
      const height = ((i % 43) / 43 - 0.5) * 4.0;
      arr[i * 3] = Math.cos(angle) * radius;
      arr[i * 3 + 1] = height;
      arr[i * 3 + 2] = Math.sin(angle) * radius;
      // Color gradient from cyan to magenta based on radius
      const t = (radius - 2.0) / 3.2;
      colors[i * 3] = 0.3 + t * 0.4;       // R
      colors[i * 3 + 1] = 0.9 - t * 0.3;   // G
      colors[i * 3 + 2] = 1.0 - t * 0.1;   // B
      sizes[i] = 0.015 + (i % 11) * 0.003;
    }
    return { positions, colors, sizes };
  }, [count]);

  useFrame((state) => {
    if (!pointsRef.current) return;
    const rot = state.clock.elapsedTime * 0.04;
    const pulse = 1 + audioAmp * 0.3;
    pointsRef.current.rotation.y = rot * (1 + audioAmp * 0.5);
    pointsRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.12 + audioAmp) * 0.05;
    pointsRef.current.scale.setScalar(pulse);
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={positions.positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={count} array={positions.colors} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial
        size={0.022}
        vertexColors
        transparent
        opacity={0.75}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
};

// ── Connector particle streams (flowing between rings) ──
const ConnectorStreams = ({ audioAmp = 0, count = 120 }) => {
  const lineRef = useRef();

  const { positions, targetPositions } = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const targ = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const t = i / count;
      const angle = t * Math.PI * 4;
      const r1 = 1.4 + t * 2.0;
      const r2 = 1.8 + (1 - t) * 1.8;
      pos[i * 3] = Math.cos(angle) * r1;
      pos[i * 3 + 1] = Math.sin(angle * 0.7) * 0.5;
      pos[i * 3 + 2] = Math.sin(angle) * r1;
      targ[i * 3] = Math.cos(angle + 0.5) * r2;
      targ[i * 3 + 1] = Math.sin(angle * 0.7 + 0.3) * 0.8;
      targ[i * 3 + 2] = Math.sin(angle + 0.5) * r2;
    }
    return { positions: pos, targetPositions: targ };
  }, [count]);

  useFrame((state) => {
    if (!lineRef.current) return;
    const p = lineRef.current.geometry.attributes.position;
    const t = (Math.sin(state.clock.elapsedTime * 0.3) * 0.5 + 0.5) * (0.6 + audioAmp * 0.4);
    const arr = p.array;
    for (let i = 0; i < count; i++) {
      arr[i * 3] += (targetPositions[i * 3] - arr[i * 3]) * 0.008;
      arr[i * 3 + 1] += (targetPositions[i * 3 + 1] - arr[i * 3 + 1]) * 0.008;
      arr[i * 3 + 2] += (targetPositions[i * 3 + 2] - arr[i * 3 + 2]) * 0.008;
    }
    p.needsUpdate = true;
  });

  return (
    <line ref={lineRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
      </bufferGeometry>
      <lineBasicMaterial color="#62f5ff" transparent opacity={0.25} blending={THREE.AdditiveBlending} />
    </line>
  );
};

// ── Scanline overlay (2D canvas — uses requestAnimationFrame, NOT useFrame) ──
const ScanlineOverlay = ({ connected }) => {
  const canvasRef = useRef();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let raf;
    let startTime = performance.now();

    // Match canvas pixel dimensions to its CSS box
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    const draw = () => {
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      const cssW = canvas.width / dpr;
      const cssH = canvas.height / dpr;
      const elapsed = (performance.now() - startTime) / 1000;
      ctx.clearRect(0, 0, cssW, cssH);

      // Scanlines
      ctx.fillStyle = `rgba(67, 234, 255, ${connected ? 0.04 : 0.02})`;
      for (let y = 0; y < cssH; y += 4) {
        ctx.fillRect(0, y, cssW, 1);
      }

      // Moving scan bar
      const scanY = ((elapsed * 0.4) % 1) * cssH;
      const gradient = ctx.createLinearGradient(0, scanY - 30, 0, scanY + 30);
      gradient.addColorStop(0, 'rgba(67, 234, 255, 0)');
      gradient.addColorStop(0.5, `rgba(67, 234, 255, ${connected ? 0.06 : 0.03})`);
      gradient.addColorStop(1, 'rgba(67, 234, 255, 0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, scanY - 30, cssW, 60);

      // Corner glows
      const glowSize = 80;
      const corners = [[0, 0], [cssW - glowSize, 0], [0, cssH - glowSize], [cssW - glowSize, cssH - glowSize]];
      corners.forEach(([cx, cy]) => {
        const grad = ctx.createRadialGradient(cx + glowSize / 2, cy + glowSize / 2, 0, cx + glowSize / 2, cy + glowSize / 2, glowSize);
        grad.addColorStop(0, `rgba(67, 234, 255, ${connected ? 0.12 : 0.05})`);
        grad.addColorStop(1, 'rgba(67, 234, 255, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(cx, cy, glowSize, glowSize);
      });

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [connected]);

  return (
    <canvas ref={canvasRef}
      className="ada-core-scanlines"
      aria-hidden="true"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 3, opacity: 0.7 }}
    />
  );
};

// ── Core scene ──
const CoreScene = ({ audioAmp, connected, activeTasks }) => {
  const groupRef = useRef();
  const sphereRef = useRef();
  const glowRef = useRef();
  const { size } = useThree();

  useFrame((state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * (connected ? 0.14 + audioAmp * 0.08 : 0.045);
      groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.22) * 0.05;
    }
    if (sphereRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2.4) * 0.03 + audioAmp * 0.2;
      sphereRef.current.scale.setScalar(pulse);
      sphereRef.current.rotation.x += delta * audioAmp * 0.15;
      sphereRef.current.rotation.z += delta * audioAmp * 0.1;
    }
    if (glowRef.current) {
      const glow = 1.6 + Math.sin(state.clock.elapsedTime * 1.7) * 0.06 + activeTasks * 0.025 + audioAmp * 0.15;
      glowRef.current.scale.set(glow, glow, glow);
    }
  });

  const taskEnergy = Math.min(1, activeTasks / 5);
  const coreColor = connected ? '#16d9ff' : '#5a7890';
  const intensity = connected ? 0.86 + audioAmp : 0.22;

  return (
    <group ref={groupRef}>
      <ambientLight intensity={0.4} />
      <pointLight position={[2, 3, 4]} color="#78f7ff" intensity={2.0 + audioAmp * 2} />
      <pointLight position={[-4, -1, -3]} color="#ff9b54" intensity={0.7 + taskEnergy + audioAmp} />

      {/* Outer glow sphere */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[1.2, 64, 64]} />
        <meshBasicMaterial
          color="#04718f"
          transparent
          opacity={connected ? 0.08 + audioAmp * 0.06 : 0.03}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Main icosahedron with holographic shader */}
      <mesh ref={sphereRef}>
        <icosahedronGeometry args={[1.02, 5]} />
        <HolographicMaterial
          baseColor={coreColor}
          glowColor="#7af9ff"
          intensity={intensity}
        />
      </mesh>

      {/* Wireframe overlay */}
      <mesh>
        <icosahedronGeometry args={[1.08, 3]} />
        <meshBasicMaterial
          color="#7af9ff"
          wireframe
          transparent
          opacity={connected ? 0.2 + audioAmp * 0.1 : 0.08}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Rings with fresnel glow */}
      <FresnelRing radius={1.5} tube={0.012} color="#38ecff" speed={0.32} tilt={Math.PI / 2.2} opacity={0.4 + audioAmp * 0.15} />
      <FresnelRing radius={1.9} tube={0.008} color="#ff9a3d" speed={-0.2} tilt={Math.PI / 2.55} opacity={0.25 + taskEnergy * 0.1} />
      <FresnelRing radius={2.3} tube={0.006} color="#d957ff" speed={0.16} tilt={Math.PI / 2.05} opacity={0.15 + taskEnergy * 0.12} />
      <FresnelRing radius={2.75} tube={0.005} color="#4dffba" speed={-0.1} tilt={Math.PI / 2.75} opacity={0.18} />

      {/* Data arcs */}
      <DataArc radius={3.1} start={0.1} length={1.3} color="#46efff" speed={0.16} y={0.02} />
      <DataArc radius={3.28} start={2.8} length={0.95} color="#ffad4d" speed={-0.22} y={-0.05} />
      <DataArc radius={2.62} start={4.15} length={0.78} color="#f455ff" speed={0.28} y={0.08} />
      <DataArc radius={3.0} start={1.5} length={0.6} color="#4dffba" speed={0.12} y={0.12} />

      {/* Particle systems */}
      <AudioReactiveParticles count={350} audioAmp={audioAmp} />
      <ConnectorStreams audioAmp={audioAmp} count={120} />

      {/* Background stars */}
      <Stars radius={22} depth={26} count={1200} factor={1.8} saturation={0} fade speed={0.25} />
    </group>
  );
};

// ── HolographicCore main component ──
const HolographicCore = ({ audioAmp = 0, connected = false, activeTasks = 0 }) => {
  return (
    <div className="ada-core-stage" aria-label="ADA holographic core">
      {/* CSS fallback */}
      <div className="ada-core-fallback" aria-hidden="true">
        <div className="ada-core-css-orbit ada-core-css-orbit-a" />
        <div className="ada-core-css-orbit ada-core-css-orbit-b" />
        <div className="ada-core-css-nucleus" />
      </div>

      {/* Scanline overlay canvas */}
      <ScanlineOverlay connected={connected} />

      {/* Three.js canvas */}
      <Canvas
        className="ada-core-canvas"
        dpr={[1, 1.75]}
        camera={{ position: [0, 0.25, 7.2], fov: 47 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
          toneMapping: THREE.ACESFilmicToneMapping,
        }}
      >
        <CoreScene audioAmp={audioAmp} connected={connected} activeTasks={activeTasks} />

        <OrbitControls
          enablePan={false}
          enableZoom={false}
          autoRotate={false}
          minPolarAngle={Math.PI / 2.5}
          maxPolarAngle={Math.PI / 1.65}
        />
      </Canvas>
    </div>
  );
};

export default HolographicCore;
