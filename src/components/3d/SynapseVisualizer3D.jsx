import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export default function SynapseVisualizer3D({ vibe, dreamState, pcmIntensity }) {
    const pointsRef = useRef();
    const linesRef = useRef();
    const count = 100;

    // Generate random 3D points inside a sphere representing the neural cluster
    const [particles, connections] = useMemo(() => {
        const positions = new Float32Array(count * 3);
        const velocities = [];
        
        for (let i = 0; i < count; i++) {
            const r = Math.random() * 2.2 + 0.3;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(Math.random() * 2 - 1);
            
            const x = r * Math.sin(phi) * Math.cos(theta);
            const y = r * Math.sin(phi) * Math.sin(theta);
            const z = r * Math.cos(phi);
            
            positions[i * 3] = x;
            positions[i * 3 + 1] = y;
            positions[i * 3 + 2] = z;
            
            velocities.push(new THREE.Vector3(
                (Math.random() - 0.5) * 0.08,
                (Math.random() - 0.5) * 0.08,
                (Math.random() - 0.5) * 0.08
            ));
        }

        // Core index connections between close nodes
        const linePositions = [];
        for (let i = 0; i < count; i++) {
            for (let j = i + 1; j < count; j++) {
                const dx = positions[i * 3] - positions[j * 3];
                const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
                const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
                
                if (dist < 1.05) {
                    linePositions.push(i, j);
                }
            }
        }

        return [
            { positions, velocities },
            new Uint16Array(linePositions)
        ];
    }, []);

    // Get color theme based on active emotive vibes and dreaming states
    const color = useMemo(() => {
        if (dreamState) return new THREE.Color('#c084fc'); // Neon Amethyst Purple
        if (vibe === 'Stressed') return new THREE.Color('#10b981'); // Soothing Emerald Green
        if (vibe === 'High-Energy') return new THREE.Color('#facc15'); // Vibrant Gold Yellow
        return new THREE.Color('#22d3ee'); // Glowing Electric Cyan
    }, [vibe, dreamState]);

    const tempV = new THREE.Vector3();

    useFrame((state) => {
        const time = state.clock.getElapsedTime();
        const positions = pointsRef.current.geometry.attributes.position.array;
        
        // 1. Move particles slowly with organic wave drift
        for (let i = 0; i < count; i++) {
            const v = particles.velocities[i];
            
            // Add sinusoidal organic wave oscillation
            positions[i * 3] += v.x * 0.04 + Math.sin(time * 0.5 + i) * 0.0012;
            positions[i * 3 + 1] += v.y * 0.04 + Math.cos(time * 0.4 + i * 1.5) * 0.0012;
            positions[i * 3 + 2] += v.z * 0.04 + Math.sin(time * 0.6 + i * 2.0) * 0.0012;
            
            // Boundary check: bounce inside a sphere of radius 3.2
            tempV.set(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]);
            if (tempV.length() > 3.2) {
                v.multiplyScalar(-1.0);
            }
        }
        
        pointsRef.current.geometry.attributes.position.needsUpdate = true;

        // 2. Re-render dynamic synapse connection lines
        const lineGeo = linesRef.current.geometry;
        const linePos = [];
        const indices = connections;
        
        for (let k = 0; k < indices.length; k += 2) {
            const idxA = indices[k];
            const idxB = indices[k + 1];
            
            linePos.push(
                positions[idxA * 3], positions[idxA * 3 + 1], positions[idxA * 3 + 2],
                positions[idxB * 3], positions[idxB * 3 + 1], positions[idxB * 3 + 2]
            );
        }
        
        lineGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(linePos), 3));
        lineGeo.attributes.position.needsUpdate = true;
        
        // Dynamic size pulse mapped to voice audio intensity
        const scaleVal = dreamState ? 1.4 : 1.0;
        const pulse = (1.0 + Math.sin(time * 6.0) * 0.12 + (pcmIntensity * 2.2)) * scaleVal;
        pointsRef.current.material.size = pulse * 0.12;
        
        // Pulsing glow rate on line synapses
        const lineOpacity = 0.22 + Math.sin(time * 3.0) * 0.08 + (pcmIntensity * 0.5);
        linesRef.current.material.opacity = Math.min(Math.max(lineOpacity, 0.1), 0.85);
    });

    return (
        <group scale={[1.2, 1.2, 1.2]} position={[0, -0.4, 0]}>
            {/* Glowing particle nodes */}
            <points ref={pointsRef}>
                <bufferGeometry>
                    <bufferAttribute
                        attachObject={['attributes', 'position']}
                        count={count}
                        array={particles.positions}
                        itemSize={3}
                    />
                </bufferGeometry>
                <pointsMaterial
                    color={color}
                    size={0.12}
                    transparent
                    opacity={0.95}
                    sizeAttenuation
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </points>

            {/* Glowing synapse linkage lines */}
            <lineSegments ref={linesRef}>
                <bufferGeometry />
                <lineBasicMaterial
                    color={color}
                    transparent
                    opacity={0.25}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </lineSegments>
        </group>
    );
}
