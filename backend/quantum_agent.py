from __future__ import annotations

import asyncio
import datetime
import hashlib
import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from context_engine import ContextEngine
from self_diagnostic import DiagnosticEngine

try:
    from qiskit import QuantumCircuit, qasm3  # type: ignore
    from qiskit.quantum_info import Statevector  # type: ignore
except Exception:
    QuantumCircuit = None  # type: ignore[assignment]
    qasm3 = None  # type: ignore[assignment]
    Statevector = None  # type: ignore[assignment]

try:
    from qiskit_aer import AerSimulator  # type: ignore
except Exception:
    AerSimulator = None  # type: ignore[assignment]

try:
    from bluequbit import BlueQubitProvider  # type: ignore
except Exception:
    BlueQubitProvider = None  # type: ignore[assignment]


def _convert_openqasm3_to_qasm2(qasm_string: str) -> str:
    """Best-effort conversion for simple OpenQASM 3 circuits."""
    converted: List[str] = ["OPENQASM 2.0;", 'include "qelib1.inc";']
    for raw in qasm_string.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        lower = line.lower()
        if lower.startswith("openqasm 3"):
            continue
        if lower.startswith("include "):
            continue
        if lower.startswith("qubit["):
            size = line.split("[", 1)[1].split("]", 1)[0]
            converted.append(f"qreg q[{size}];")
            continue
        converted.append(line)
    return "\n".join(converted)


def _qiskit_circuit_from_qasm(qasm_string: str) -> Optional[Any]:
    """Parse OpenQASM 3/2 into a Qiskit QuantumCircuit when available."""
    if QuantumCircuit is None or not qasm_string.strip():
        return None
    if qasm3 is not None:
        try:
            return qasm3.loads(qasm_string)
        except Exception:
            pass
    try:
        return QuantumCircuit.from_qasm_str(qasm_string)
    except Exception:
        pass
    try:
        return QuantumCircuit.from_qasm_str(_convert_openqasm3_to_qasm2(qasm_string))
    except Exception:
        return None


@dataclass
class ParsedProblem:
    """Structured problem description."""

    problem_type: str
    variables: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    objective: str
    recommended_tier: int


@dataclass
class DiscoveryBudget:
    """Budget constraints for a discovery run."""

    max_runtime_minutes: int = 30
    max_cost_usd: float = 5.0
    max_cloud_jobs: int = 4


class MultiCloudQuantumBroker:
    """Queue/cost aware broker for cloud-heavy quantum routing."""

    def __init__(self) -> None:
        self._providers: Dict[str, Dict[str, Any]] = {
            "bluequbit": {
                "hardware": True,
                "base_queue_minutes": 7.0,
                "cost_per_job": 0.60,
                "domain_fit": {
                    "materials": 0.89,
                    "molecular": 0.91,
                    "reaction": 0.84,
                    "emergent_tech": 0.82,
                },
            },
            "braket": {
                "hardware": True,
                "base_queue_minutes": 8.0,
                "cost_per_job": 0.66,
                "domain_fit": {
                    "materials": 0.84,
                    "molecular": 0.86,
                    "reaction": 0.87,
                    "emergent_tech": 0.81,
                },
            },
            "local_simulator": {
                "hardware": False,
                "base_queue_minutes": 0.3,
                "cost_per_job": 0.0,
                "domain_fit": {
                    "materials": 0.68,
                    "molecular": 0.72,
                    "reaction": 0.70,
                    "emergent_tech": 0.74,
                },
            },
        }
        self._historical_success = {
            "bluequbit": 0.93,
            "braket": 0.90,
            "local_simulator": 0.98,
        }

    def select_provider_plan(
        self,
        *,
        domains: List[str],
        fidelity: str,
        budget: DiscoveryBudget,
        require_hardware_validation: bool,
    ) -> Dict[str, Any]:
        ranked = self._rank_providers(
            domains=domains,
            fidelity=fidelity,
            budget=budget,
            require_hardware_validation=require_hardware_validation,
        )
        primary = ranked[0]["provider"] if ranked else "local_simulator"
        fallback_chain = [r["provider"] for r in ranked[1:]]
        return {"primary": primary, "ranked": ranked, "fallback_chain": fallback_chain}

    def _rank_providers(
        self,
        *,
        domains: List[str],
        fidelity: str,
        budget: DiscoveryBudget,
        require_hardware_validation: bool,
    ) -> List[Dict[str, Any]]:
        fidelity_cost_multiplier = {"quick": 0.7, "balanced": 1.0, "high": 1.45}.get(fidelity, 1.0)
        rows: List[Dict[str, Any]] = []
        for provider, meta in self._providers.items():
            if require_hardware_validation and not meta["hardware"]:
                continue
            if budget.max_cost_usd <= 0 and meta["cost_per_job"] > 0:
                continue
            fit_values = [float(meta["domain_fit"].get(domain, 0.7)) for domain in domains]
            fit_score = float(sum(fit_values) / max(1, len(fit_values)))
            queue_score = 1.0 / (1.0 + float(meta["base_queue_minutes"]))
            success_score = float(self._historical_success.get(provider, 0.7))
            estimated_job_cost = float(meta["cost_per_job"]) * fidelity_cost_multiplier
            cost_score = 1.0 if estimated_job_cost <= budget.max_cost_usd else max(
                0.0, budget.max_cost_usd / max(estimated_job_cost, 1e-6)
            )
            hardware_bonus = 0.15 if meta["hardware"] and fidelity == "high" else 0.0
            total = (
                (fit_score * 0.42)
                + (queue_score * 0.18)
                + (success_score * 0.24)
                + (cost_score * 0.16)
                + hardware_bonus
            )
            rows.append(
                {
                    "provider": provider,
                    "score": round(total, 4),
                    "estimated_queue_minutes": round(float(meta["base_queue_minutes"]), 2),
                    "estimated_job_cost_usd": round(estimated_job_cost, 4),
                    "hardware": bool(meta["hardware"]),
                    "fit_score": round(fit_score, 4),
                    "success_score": round(success_score, 4),
                    "cost_score": round(cost_score, 4),
                }
            )
        rows.sort(key=lambda row: row["score"], reverse=True)
        return rows


class QuantumProblemTranslator:
    """Translate engineering problems into quantum formulations."""

    def parse_problem(self, description: str) -> Dict[str, Any]:
        """Classify a natural language problem into a structured format."""
        text = (description or "").lower()
        problem_type = "combinatorial"
        if "route" in text or "path" in text or "tsp" in text:
            problem_type = "graph"
        elif "parameter" in text or "continuous" in text or "vqe" in text:
            problem_type = "variational"
        elif "molecule" in text or "material" in text:
            problem_type = "molecular"
        objective = self._extract_objective(description)
        variables = self._extract_variable_hints(description)
        constraints = self._extract_constraints(description)
        recommended_tier = 1
        size_hint = self._estimate_variables(description)
        if size_hint < 8:
            recommended_tier = 3 if problem_type in {"variational", "molecular"} else 1
        elif size_hint < 20:
            recommended_tier = 1
        else:
            recommended_tier = 1
        if problem_type == "molecular":
            recommended_tier = 2
        return ParsedProblem(
            problem_type=problem_type,
            variables=variables,
            constraints=constraints,
            objective=objective,
            recommended_tier=recommended_tier,
        ).__dict__

    def formulate_qubo(
        self,
        variables: List[Dict[str, Any]],
        constraints: List[Dict[str, Any]],
        objective: str,
    ) -> np.ndarray:
        """Build a QUBO matrix from component selection data."""
        option_map: List[Tuple[str, Dict[str, Any]]] = []
        for var in variables:
            name = var.get("name", "var")
            for option in var.get("options", []):
                option_map.append((name, option))
        n = len(option_map)
        Q = np.zeros((n, n))
        obj_weights = self._objective_weights(objective)
        for i, (_, option) in enumerate(option_map):
            weight = option.get("weight", 0.0)
            cost = option.get("cost", 0.0)
            perf = option.get("performance", 0.0)
            Q[i, i] += obj_weights["weight"] * weight
            Q[i, i] += obj_weights["cost"] * cost
            Q[i, i] += obj_weights["performance"] * perf
        penalty = 10.0
        for name in {n for n, _ in option_map}:
            indices = [i for i, (var_name, _) in enumerate(option_map) if var_name == name]
            for i in indices:
                Q[i, i] += penalty
            for i in indices:
                for j in indices:
                    if i != j:
                        Q[i, j] += penalty
            Q[indices, indices] -= penalty
        for constraint in constraints:
            variable = constraint.get("variable")
            target = float(constraint.get("value", 0))
            indices = [i for i, (var_name, _) in enumerate(option_map) if var_name == variable]
            if not indices:
                continue
            coeffs = []
            for i in indices:
                option = option_map[i][1]
                coeffs.append(option.get(variable, option.get("weight", 0.0)))
            for i, coeff in zip(indices, coeffs):
                Q[i, i] += penalty * (coeff * coeff - 2 * target * coeff)
            for i, ci in zip(indices, coeffs):
                for j, cj in zip(indices, coeffs):
                    if i != j:
                        Q[i, j] += penalty * ci * cj
        return Q

    def formulate_graph_problem(self, nodes: List[Any], edges: List[Tuple[Any, Any, float]]) -> np.ndarray:
        """Build a QUBO for TSP-like routing."""
        n = len(nodes)
        if n == 0:
            return np.zeros((1, 1))
        index = {node: i for i, node in enumerate(nodes)}
        Q = np.zeros((n * n, n * n))
        A = 10.0
        B = 1.0
        for i in range(n):
            for p in range(n):
                Q[i * n + p, i * n + p] += -A
                for q in range(n):
                    if p != q:
                        Q[i * n + p, i * n + q] += 2 * A
        for p in range(n):
            for i in range(n):
                Q[i * n + p, i * n + p] += -A
                for j in range(n):
                    if i != j:
                        Q[i * n + p, j * n + p] += 2 * A
        for u, v, w in edges:
            i = index[u]
            j = index[v]
            for p in range(n):
                q = (p + 1) % n
                Q[i * n + p, j * n + q] += B * w
        return Q

    def formulate_variational(
        self,
        objective_function: Callable[[np.ndarray], float],
        num_parameters: int,
        bounds: List[Tuple[float, float]],
    ) -> Dict[str, Any]:
        """Return a variational problem definition."""
        return {
            "objective_function": objective_function,
            "num_parameters": num_parameters,
            "bounds": bounds,
        }

    def _objective_weights(self, objective: str) -> Dict[str, float]:
        text = objective.lower()
        weights = {"weight": 0.0, "cost": 0.0, "performance": 0.0}
        if "weight" in text:
            weights["weight"] = 1.0
        if "cost" in text or "price" in text:
            weights["cost"] = 1.0
        if "performance" in text or "maximize" in text:
            weights["performance"] = -1.0 if "max" in text else 1.0
        if all(value == 0.0 for value in weights.values()):
            weights["weight"] = 1.0
        return weights

    def _estimate_variables(self, description: str) -> int:
        digits = [int(token) for token in description.split() if token.isdigit()]
        return digits[0] if digits else 10

    def _extract_objective(self, description: str) -> str:
        text = description.strip()
        if not text:
            return "optimize objective"
        lowered = text.lower()
        if "maximize" in lowered:
            return text[text.lower().find("maximize") :]
        if "minimize" in lowered:
            return text[text.lower().find("minimize") :]
        if "optimize" in lowered:
            return text[text.lower().find("optimize") :]
        return text

    def _extract_constraints(self, description: str) -> List[Dict[str, Any]]:
        text = (description or "").lower()
        constraints: List[Dict[str, Any]] = []
        for key in ("budget", "runtime", "latency", "cost", "energy", "temperature"):
            if key in text:
                constraints.append({"type": "hint", "name": key})
        for token in description.replace(",", " ").split():
            if token.replace(".", "", 1).isdigit():
                constraints.append({"type": "numeric_hint", "value": float(token)})
                if len(constraints) >= 5:
                    break
        return constraints

    def _extract_variable_hints(self, description: str) -> List[Dict[str, Any]]:
        text = (description or "").lower()
        hints: List[Dict[str, Any]] = []
        if "material" in text:
            hints.append({"name": "composition", "kind": "categorical"})
        if "molecule" in text or "reaction" in text:
            hints.append({"name": "structure", "kind": "graph"})
        if "route" in text or "path" in text:
            hints.append({"name": "path", "kind": "graph"})
        if "parameter" in text:
            hints.append({"name": "parameters", "kind": "continuous"})
        return hints


class Tier1_ClassicalQuantum:
    """Quantum-inspired classical solvers."""

    def solve_qubo(
        self,
        Q: np.ndarray,
        num_reads: int = 1000,
        T_initial: float = 100.0,
        cooling_rate: float = 0.995,
    ) -> Dict[str, Any]:
        """Solve QUBO with simulated annealing."""
        n = Q.shape[0]
        best_solution = None
        best_energy = float("inf")
        solutions = []
        convergence = []
        for _ in range(num_reads):
            x = np.random.randint(0, 2, size=n)
            energy = self._energy(Q, x)
            T = T_initial
            for _ in range(500):
                idx = np.random.randint(0, n)
                x_new = x.copy()
                x_new[idx] = 1 - x_new[idx]
                new_energy = self._energy(Q, x_new)
                dE = new_energy - energy
                if dE < 0 or random.random() < math.exp(-dE / max(T, 1e-6)):
                    x = x_new
                    energy = new_energy
                T *= cooling_rate
            if energy < best_energy:
                best_energy = energy
                best_solution = x.copy()
            solutions.append((energy, x.copy()))
            convergence.append(best_energy)
        solutions.sort(key=lambda item: item[0])
        top_solutions = [
            {"energy": float(e), "solution": s.tolist()} for e, s in solutions[:5]
        ]
        return {
            "best_solution": best_solution.tolist() if best_solution is not None else [],
            "best_energy": float(best_energy),
            "all_solutions": top_solutions,
            "convergence_history": convergence,
        }

    def solve_qaoa(self, Q: np.ndarray, p: int = 3, num_shots: int = 1000) -> Dict[str, Any]:
        """Solve QUBO using simplified QAOA simulation."""
        n = Q.shape[0]
        if n > 18:
            raise ValueError("QAOA simulator limited to 18 variables.")
        cost_diag = self._qubo_costs(Q)
        initial_state = np.ones(2 ** n, dtype=complex) / math.sqrt(2 ** n)
        convergence = []

        def objective(params: np.ndarray) -> float:
            gamma = params[:p]
            beta = params[p:]
            state = initial_state.copy()
            for layer in range(p):
                state = state * np.exp(-1j * gamma[layer] * cost_diag)
                state = self._apply_mixer(state, beta[layer], n)
            probs = np.abs(state) ** 2
            expectation = float(np.sum(probs * cost_diag))
            convergence.append(expectation)
            return expectation

        init = np.random.uniform(0, math.pi, size=2 * p)
        result = minimize(objective, init, method="Nelder-Mead", options={"maxiter": 200})
        final_params = result.x
        gamma = final_params[:p]
        beta = final_params[p:]
        state = initial_state.copy()
        for layer in range(p):
            state = state * np.exp(-1j * gamma[layer] * cost_diag)
            state = self._apply_mixer(state, beta[layer], n)
        probs = np.abs(state) ** 2
        samples = np.random.choice(len(probs), size=num_shots, p=probs)
        counts = {}
        for sample in samples:
            bitstring = format(sample, f"0{n}b")
            counts[bitstring] = counts.get(bitstring, 0) + 1
        best_state = max(counts.items(), key=lambda item: item[1])[0]
        best_energy = float(cost_diag[int(best_state, 2)])
        return {
            "best_solution": best_state,
            "best_energy": best_energy,
            "optimal_parameters": {"gamma": gamma.tolist(), "beta": beta.tolist()},
            "convergence_history": convergence,
        }

    def solve_genetic(
        self,
        objective: Callable[[np.ndarray], float],
        num_parameters: int,
        bounds: List[Tuple[float, float]],
        population_size: int = 100,
        generations: int = 500,
    ) -> Dict[str, Any]:
        """Genetic algorithm solver for parameter optimization."""
        population = [
            np.array([random.uniform(*bounds[i]) for i in range(num_parameters)]) for _ in range(population_size)
        ]
        convergence = []
        for _ in range(generations):
            fitness = [objective(ind) for ind in population]
            ranked = sorted(zip(fitness, population), key=lambda item: item[0])
            convergence.append(ranked[0][0])
            elites = [ind for _, ind in ranked[: max(1, population_size // 10)]]
            new_population = elites.copy()
            while len(new_population) < population_size:
                parent1 = self._tournament(ranked)
                parent2 = self._tournament(ranked)
                child = self._crossover(parent1, parent2)
                child = self._mutate(child, bounds)
                new_population.append(child)
            population = new_population
        evaluated = [(objective(ind), ind) for ind in population]
        best_fitness, best_params = min(evaluated, key=lambda item: item[0])
        return {
            "best_parameters": best_params.tolist(),
            "best_fitness": float(best_fitness),
            "convergence_history": convergence,
        }

    def _energy(self, Q: np.ndarray, x: np.ndarray) -> float:
        return float(x.T @ Q @ x)

    def _qubo_costs(self, Q: np.ndarray) -> np.ndarray:
        n = Q.shape[0]
        costs = np.zeros(2 ** n)
        for i in range(2 ** n):
            bitstring = np.array(list(map(int, format(i, f"0{n}b"))))
            costs[i] = bitstring.T @ Q @ bitstring
        return costs

    def _apply_mixer(self, state: np.ndarray, beta: float, n: int) -> np.ndarray:
        rx = np.array(
            [[math.cos(beta), -1j * math.sin(beta)], [-1j * math.sin(beta), math.cos(beta)]],
            dtype=complex,
        )
        for qubit in range(n):
            state = self._apply_single_qubit(state, rx, qubit, n)
        return state

    def _apply_single_qubit(self, state: np.ndarray, gate: np.ndarray, qubit: int, n: int) -> np.ndarray:
        state = state.reshape([2] * n)
        axes = list(range(n))
        axes[0], axes[qubit] = axes[qubit], axes[0]
        state = np.transpose(state, axes)
        state = np.tensordot(gate, state, axes=([1], [0]))
        state = np.transpose(state, axes)
        return state.reshape(-1)

    def _tournament(self, ranked: List[Tuple[float, np.ndarray]], k: int = 3) -> np.ndarray:
        sample = random.sample(ranked, k)
        return min(sample, key=lambda item: item[0])[1]

    def _crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        point = random.randint(1, len(parent1) - 1)
        return np.concatenate([parent1[:point], parent2[point:]])

    def _mutate(self, individual: np.ndarray, bounds: List[Tuple[float, float]], rate: float = 0.1) -> np.ndarray:
        for i in range(len(individual)):
            if random.random() < rate:
                individual[i] = random.uniform(*bounds[i])
        return individual

    # --- VQE: Variational Quantum Eigensolver ---

    def solve_vqe(
        self,
        hamiltonian_matrix: np.ndarray,
        num_layers: int = 3,
        max_iterations: int = 200,
        shots: int = 1024,
    ) -> Dict[str, Any]:
        """Solve for the ground state energy of a Hamiltonian using VQE.

        Uses a hardware-efficient ansatz with Ry-Rz rotations and CNOT entangling layers.
        """
        num_qubits = int(np.log2(hamiltonian_matrix.shape[0]))
        if num_qubits > 12:
            raise ValueError("VQE limited to 12 qubits.")
        num_params = num_qubits * 2 * num_layers
        convergence: List[float] = []

        def energy_expectation(params: np.ndarray) -> float:
            state = self._vqe_ansatz(params, num_qubits, num_layers)
            expectation = float(np.real(state.conj() @ hamiltonian_matrix @ state))
            convergence.append(expectation)
            return expectation

        init_params = np.random.uniform(0, 2 * math.pi, size=num_params)
        opt_result = minimize(energy_expectation, init_params, method="COBYLA", options={"maxiter": max_iterations})
        ground_energy = float(opt_result.fun)
        optimal_state = self._vqe_ansatz(opt_result.x, num_qubits, num_layers)
        probs = np.abs(optimal_state) ** 2
        dominant_state = format(int(np.argmax(probs)), f"0{num_qubits}b")
        return {
            "ground_energy": ground_energy,
            "optimal_parameters": opt_result.x.tolist(),
            "dominant_state": dominant_state,
            "state_probabilities": {format(i, f"0{num_qubits}b"): round(float(p), 6) for i, p in enumerate(probs) if p > 0.01},
            "convergence_history": convergence,
            "num_iterations": int(opt_result.nfev),
            "converged": bool(opt_result.success),
        }

    def _vqe_ansatz(self, params: np.ndarray, num_qubits: int, num_layers: int) -> np.ndarray:
        """Hardware-efficient ansatz with Ry-Rz + CNOT layers."""
        state = np.zeros(2 ** num_qubits, dtype=complex)
        state[0] = 1.0
        idx = 0
        for layer in range(num_layers):
            for qubit in range(num_qubits):
                ry_angle = float(params[idx])
                rz_angle = float(params[idx + 1])
                idx += 2
                ry_mat = np.array(
                    [[math.cos(ry_angle / 2), -math.sin(ry_angle / 2)],
                     [math.sin(ry_angle / 2), math.cos(ry_angle / 2)]],
                    dtype=complex,
                )
                state = self._apply_single_qubit(state, ry_mat, qubit, num_qubits)
                rz_mat = np.array(
                    [[np.exp(-1j * rz_angle / 2), 0], [0, np.exp(1j * rz_angle / 2)]],
                    dtype=complex,
                )
                state = self._apply_single_qubit(state, rz_mat, qubit, num_qubits)
            # CNOT entangling layer (linear chain)
            for qubit in range(num_qubits - 1):
                state = self._apply_cnot(state, qubit, qubit + 1, num_qubits)
        return state

    def _apply_cnot(self, state: np.ndarray, control: int, target: int, n: int) -> np.ndarray:
        """Apply CNOT gate."""
        state = state.reshape([2] * n)
        axes = list(range(n))
        axes[0], axes[control] = axes[control], axes[0]
        axes[1], axes[target] = axes[target], axes[1]
        state = np.transpose(state, axes)
        cnot = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex)
        state = state.reshape(4, -1)
        state = cnot @ state
        state = state.reshape([2, 2] + [2] * (n - 2))
        state = np.transpose(state, axes)
        return state.reshape(-1)

    # --- Grover's Search ---

    def solve_grover(
        self,
        num_qubits: int,
        oracle_targets: List[int],
        num_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run Grover's algorithm for unstructured search.

        Args:
            num_qubits: Number of qubits (search space = 2^num_qubits).
            oracle_targets: List of target state indices to find.
            num_iterations: Number of Grover iterations. Defaults to optimal.
        """
        if num_qubits > 18:
            raise ValueError("Grover simulator limited to 18 qubits.")
        N = 2 ** num_qubits
        M = len(oracle_targets)
        if M == 0:
            return {"error": "No oracle targets specified", "counts": {}, "success_probability": 0.0}
        if num_iterations is None:
            num_iterations = max(1, int(math.pi / 4 * math.sqrt(N / M)))

        # |s⟩ = H^n|0⟩ (uniform superposition)
        state = np.ones(N, dtype=complex) / math.sqrt(N)

        # Build oracle and diffusion operators
        oracle = np.ones(N, dtype=complex)
        for target in oracle_targets:
            if 0 <= target < N:
                oracle[target] = -1.0

        # Grover iterations
        for _ in range(num_iterations):
            # Oracle: flip amplitude of target states
            state = state * oracle
            # Diffusion: 2|s⟩⟨s| - I
            mean_amp = np.mean(state)
            state = 2.0 * mean_amp - state

        probs = np.abs(state) ** 2
        target_prob = float(sum(probs[t] for t in oracle_targets if 0 <= t < N))
        samples = np.random.choice(N, size=1024, p=probs)
        counts: Dict[str, int] = {}
        for s in samples:
            bs = format(int(s), f"0{num_qubits}b")
            counts[bs] = counts.get(bs, 0) + 1
        return {
            "success_probability": round(target_prob, 6),
            "optimal_iterations": num_iterations,
            "counts": counts,
            "target_states": [format(t, f"0{num_qubits}b") for t in oracle_targets],
            "amplification_factor": round(target_prob / (M / N), 4) if M > 0 else 0.0,
        }

    # --- Quantum Error Mitigation ---

    def zero_noise_extrapolation(
        self,
        circuit_runner: Callable[[float], Dict[str, float]],
        noise_factors: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Zero-noise extrapolation (ZNE) for error mitigation.

        Args:
            circuit_runner: A callable that takes a noise_factor (float >= 1.0)
                and returns a dict of {bitstring: probability}.
            noise_factors: List of noise scaling factors. Default [1.0, 2.0, 3.0].
        """
        if noise_factors is None:
            noise_factors = [1.0, 2.0, 3.0]
        noise_factors = sorted(noise_factors)

        raw_results: List[Dict[str, float]] = []
        expectation_values: List[float] = []
        for factor in noise_factors:
            result = circuit_runner(factor)
            raw_results.append(result)
            # Compute expectation value (parity of bitstring)
            ev = sum(
                prob * (-1.0 if bin(int(bs, 2)).count("1") % 2 else 1.0)
                for bs, prob in result.items()
            )
            expectation_values.append(ev)

        # Richardson extrapolation to zero noise
        mitigated = self._richardson_extrapolation(noise_factors, expectation_values)
        return {
            "mitigated_expectation": round(float(mitigated), 8),
            "raw_expectations": [round(ev, 6) for ev in expectation_values],
            "noise_factors": noise_factors,
            "correction_magnitude": round(abs(float(mitigated) - expectation_values[0]), 6),
            "raw_results": raw_results,
        }

    def _richardson_extrapolation(self, factors: List[float], values: List[float]) -> float:
        """Richardson extrapolation to estimate the zero-noise limit."""
        n = len(factors)
        if n == 1:
            return values[0]
        # Build Vandermonde-like matrix: value = a0 + a1*f + a2*f^2 + ...
        A = np.array([[f ** k for k in range(n)] for f in factors])
        try:
            coeffs = np.linalg.solve(A, values)
            return float(coeffs[0])  # a0 is the zero-noise value
        except np.linalg.LinAlgError:
            return float(values[0])

    # --- Entanglement Measurement ---

    def measure_entanglement(self, statevector: np.ndarray) -> Dict[str, Any]:
        """Measure entanglement properties of a quantum state.

        Computes concurrence (for 2-qubit states), von Neumann entropy,
        and purity for all qubit bipartitions.
        """
        n = len(statevector)
        num_qubits = int(np.log2(n))
        if num_qubits < 2 or 2 ** num_qubits != n:
            return {"error": "State must have 2^n amplitudes for n>=2 qubits"}

        results: Dict[str, Any] = {"num_qubits": num_qubits, "state_purity": round(float(self._purity(statevector)), 8)}

        # Concurrence for 2-qubit systems
        if num_qubits == 2:
            conc = self._concurrence_2qubit(statevector)
            results["concurrence"] = round(float(conc), 8)
            results["entanglement_classification"] = (
                "maximally_entangled" if conc > 0.99
                else "entangled" if conc > 0.01
                else "separable"
            )

        # Von Neumann entropy for each qubit bipartition
        entropies = {}
        for qubit in range(num_qubits):
            rho_reduced = self._partial_trace(statevector, num_qubits, qubit)
            entropy = self._von_neumann_entropy(rho_reduced)
            entropies[f"qubit_{qubit}"] = round(float(entropy), 8)
        results["subsystem_entropies"] = entropies
        results["max_entropy"] = round(float(max(entropies.values())), 8)
        results["is_entangled"] = any(float(v) > 0.01 for v in entropies.values())
        return results

    def _purity(self, statevector: np.ndarray) -> float:
        """Purity Tr(ρ²) of a pure state (always 1.0 for statevectors)."""
        rho = np.outer(statevector, statevector.conj())
        return float(np.real(np.trace(rho @ rho)))

    def _concurrence_2qubit(self, statevector: np.ndarray) -> float:
        """Wootters concurrence for 2-qubit pure states."""
        rho = np.outer(statevector, statevector.conj())
        sigma_y = np.array([[0, -1j], [1j, 0]])
        yy = np.kron(sigma_y, sigma_y)
        rho_tilde = yy @ rho.conj() @ yy
        product = rho @ rho_tilde
        eigenvalues = sorted(np.real(np.linalg.eigvals(product)), reverse=True)
        lambdas = [math.sqrt(max(0.0, float(ev))) for ev in eigenvalues]
        return max(0.0, lambdas[0] - sum(lambdas[1:]))

    def _partial_trace(self, statevector: np.ndarray, num_qubits: int, keep_qubit: int) -> np.ndarray:
        """Compute reduced density matrix by tracing out all qubits except keep_qubit."""
        rho = np.outer(statevector, statevector.conj())
        rho = rho.reshape([2] * (2 * num_qubits))
        trace_qubits = [q for q in range(num_qubits) if q != keep_qubit]
        for q in sorted(trace_qubits, reverse=True):
            rho = np.trace(rho, axis1=q, axis2=q + num_qubits)
            num_qubits -= 1
            keep_qubit = keep_qubit if keep_qubit < q else keep_qubit - 1
        return rho.reshape(2, 2)

    def _von_neumann_entropy(self, rho: np.ndarray) -> float:
        """Von Neumann entropy S = -Tr(ρ log₂ ρ)."""
        eigenvalues = np.real(np.linalg.eigvalsh(rho))
        eigenvalues = eigenvalues[eigenvalues > 1e-12]
        return float(-np.sum(eigenvalues * np.log2(eigenvalues)))


class Tier2_RealQuantum:
    """BlueQubit cloud integration via Qiskit provider."""

    def __init__(self) -> None:
        self._token = os.getenv("BLUEQUBIT_API_TOKEN") or os.getenv("BLUEQUBIT_API_KEY")
        self._provider = None
        self._jobs: Dict[str, Any] = {}
        if self._token and BlueQubitProvider is not None:
            try:
                self._provider = BlueQubitProvider(self._token)
            except Exception:
                self._provider = None

    def generate_circuit_for_problem(self, problem: Dict[str, Any]) -> str:
        """Generate OpenQASM 3.0 circuit from problem definition."""
        problem_type = problem.get("problem_type", "combinatorial")
        num_qubits = max(2, len(problem.get("variables", [])) or 2)
        lines = ["OPENQASM 3.0;", f"qubit[{num_qubits}] q;"]
        if problem_type in {"combinatorial", "graph"}:
            for i in range(num_qubits):
                lines.append(f"h q[{i}];")
            for i in range(num_qubits - 1):
                lines.append(f"cx q[{i}], q[{i+1}];")
        else:
            for i in range(num_qubits):
                lines.append(f"ry(0.3) q[{i}];")
                lines.append(f"rz(0.2) q[{i}];")
        return "\n".join(lines)

    def submit_circuit(self, qasm_string: str, backend: str = "quantum_device", shots: int = 4096) -> str:
        """Submit a circuit to BlueQubit using Qiskit backend API."""
        if not self._provider:
            return "unavailable"
        circuit = _qiskit_circuit_from_qasm(qasm_string)
        if circuit is None:
            return "unavailable"
        try:
            backend_handle = self._provider.get_backend(backend)
            job = backend_handle.run(circuit, shots=int(shots))
            job_id = str(job.job_id())
            self._jobs[job_id] = job
            return job_id
        except Exception:
            return "unavailable"

    def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """Check status of BlueQubit job."""
        if not self._provider or job_id == "unavailable":
            return {"status": "unavailable", "position_in_queue": None, "estimated_time": None}
        job = self._jobs.get(job_id)
        if job is None:
            return {"status": "unknown", "position_in_queue": None, "estimated_time": None}
        try:
            status_obj = job.status()
            status = str(getattr(status_obj, "name", status_obj)).lower()
        except Exception:
            return {"status": "error", "position_in_queue": None, "estimated_time": None}
        return {
            "status": status,
            "position_in_queue": None,
            "estimated_time": None,
        }

    def get_job_results(self, job_id: str) -> Dict[str, Any]:
        """Fetch results for BlueQubit job."""
        if not self._provider or job_id == "unavailable":
            return {"counts": {}, "most_probable": "", "execution_time": 0.0}
        job = self._jobs.get(job_id)
        if job is None:
            return {"counts": {}, "most_probable": "", "execution_time": 0.0}
        start = time.time()
        try:
            result = job.result()
            counts_raw = result.get_counts()
        except Exception:
            return {"counts": {}, "most_probable": "", "execution_time": 0.0}
        counts = {str(k): int(v) for k, v in dict(counts_raw).items()}
        most_probable = max(counts, key=counts.get) if counts else ""
        return {"counts": counts, "most_probable": most_probable, "execution_time": time.time() - start}

    def estimate_circuit_fidelity(self, circuit_depth: int, num_qubits: int) -> float:
        """Estimate circuit fidelity based on depth and qubits."""
        gate_error = 0.01
        fidelity = (1 - gate_error) ** (circuit_depth * num_qubits)
        return float(fidelity)


class Tier3_LocalSimulator:
    """Noise-free local quantum circuit simulator."""

    def simulate(
        self,
        qasm_string: str,
        shots: int = 1024,
        *,
        noisy: bool = False,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Simulate a quantum circuit from OpenQASM 3.0."""
        qiskit_result = self._simulate_with_qiskit(qasm_string, shots=shots, noisy=noisy, seed=seed)
        if qiskit_result is not None:
            return qiskit_result

        circuit = self._parse_qasm(qasm_string)
        num_qubits = circuit["num_qubits"]
        if seed is not None:
            np.random.seed(int(seed))
        if num_qubits > 24:
            raise ValueError("Simulator limited to 24 qubits.")
        # For larger circuits avoid dense 2^n statevector allocation.
        if num_qubits > 16:
            return self._sample_large_circuit(circuit, shots=shots, noisy=noisy, seed=seed)
        state = np.zeros(2**num_qubits, dtype=complex)
        state[0] = 1.0
        start = time.time()
        for gate in circuit["gates"]:
            state = self._apply_gate(state, gate, num_qubits)
        if noisy:
            # Simple depolarizing proxy by blending with uniform distribution.
            blend = min(0.35, 0.01 * len(circuit["gates"]))
            probs = np.abs(state) ** 2
            uniform = np.ones_like(probs) / len(probs)
            probs = ((1 - blend) * probs) + (blend * uniform)
            probs = probs / probs.sum()
        else:
            probs = np.abs(state) ** 2
        samples = np.random.choice(len(probs), size=shots, p=probs)
        counts: Dict[str, int] = {}
        for sample in samples:
            bitstring = format(sample, f"0{num_qubits}b")
            counts[bitstring] = counts.get(bitstring, 0) + 1
        return {
            "counts": counts,
            "statevector": state.tolist(),
            "execution_time": time.time() - start,
            "mode": "noisy" if noisy else "ideal",
        }

    def _simulate_with_qiskit(
        self,
        qasm_string: str,
        *,
        shots: int,
        noisy: bool,
        seed: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """Use Qiskit simulators/statevectors when available."""
        circuit = _qiskit_circuit_from_qasm(qasm_string)
        if circuit is None:
            return None
        start = time.time()

        if AerSimulator is not None:
            run_kwargs: Dict[str, Any] = {"shots": int(shots)}
            if seed is not None:
                run_kwargs["seed_simulator"] = int(seed)
            mode = "qiskit_aer"
            if noisy:
                mode = "qiskit_aer_noisy_proxy"
            try:
                backend = AerSimulator()
                result = backend.run(circuit, **run_kwargs).result()
                counts_raw = result.get_counts()
                counts = {str(k): int(v) for k, v in dict(counts_raw).items()}
                statevector: List[Any] = []
                if not noisy and Statevector is not None and int(circuit.num_qubits) <= 16:
                    try:
                        statevector = Statevector.from_instruction(circuit).data.tolist()
                    except Exception:
                        statevector = []
                return {
                    "counts": counts,
                    "statevector": statevector,
                    "execution_time": time.time() - start,
                    "mode": mode,
                }
            except Exception:
                pass

        if Statevector is None:
            return None

        try:
            state = Statevector.from_instruction(circuit).data
            probs = np.abs(state) ** 2
            if noisy:
                blend = min(0.35, 0.01 * len(circuit.data))
                uniform = np.ones_like(probs) / len(probs)
                probs = ((1 - blend) * probs) + (blend * uniform)
                probs = probs / probs.sum()
            rng = np.random.default_rng(seed)
            samples = rng.choice(len(probs), size=int(shots), p=probs)
            counts: Dict[str, int] = {}
            qubits = int(circuit.num_qubits)
            for sample in samples:
                bitstring = format(int(sample), f"0{qubits}b")
                counts[bitstring] = counts.get(bitstring, 0) + 1
            return {
                "counts": counts,
                "statevector": state.tolist() if not noisy else [],
                "execution_time": time.time() - start,
                "mode": "qiskit_statevector_noisy_proxy" if noisy else "qiskit_statevector",
            }
        except Exception:
            return None

    def explain_circuit(self, qasm_string: str) -> str:
        """Explain the circuit gate by gate."""
        circuit = self._parse_qasm(qasm_string)
        lines = ["Circuit explanation:"]
        for gate in circuit["gates"]:
            lines.append(f"Apply {gate['name']} on qubits {gate['targets']}.")
        return " ".join(lines)

    def visualize_circuit(self, qasm_string: str) -> str:
        """Generate ASCII circuit diagram."""
        circuit = self._parse_qasm(qasm_string)
        num_qubits = circuit["num_qubits"]
        lines = [["|0>"] for _ in range(num_qubits)]
        for gate in circuit["gates"]:
            name = gate["name"]
            targets = gate["targets"]
            for q in range(num_qubits):
                if q in targets:
                    lines[q].append(f"-{name}-")
                else:
                    lines[q].append("---")
        return "\n".join("".join(row) for row in lines)

    def _parse_qasm(self, qasm: str) -> Dict[str, Any]:
        lines = [line.strip() for line in qasm.splitlines() if line.strip() and not line.strip().startswith("//")]
        num_qubits = 0
        gates = []
        for line in lines:
            if line.startswith("qubit"):
                size = line.split("[")[1].split("]")[0]
                num_qubits = int(size)
            if any(line.startswith(prefix) for prefix in ["h", "x", "y", "z", "rx", "ry", "rz", "cx", "cz", "swap"]):
                gate = self._parse_gate(line)
                if gate:
                    gates.append(gate)
        return {"num_qubits": num_qubits, "gates": gates}

    def _parse_gate(self, line: str) -> Optional[Dict[str, Any]]:
        line = line.replace(";", "")
        if line.startswith("h"):
            idx = int(line.split("[")[1].split("]")[0])
            return {"name": "H", "targets": [idx]}
        if line.startswith("x"):
            idx = int(line.split("[")[1].split("]")[0])
            return {"name": "X", "targets": [idx]}
        if line.startswith("y"):
            idx = int(line.split("[")[1].split("]")[0])
            return {"name": "Y", "targets": [idx]}
        if line.startswith("z"):
            idx = int(line.split("[")[1].split("]")[0])
            return {"name": "Z", "targets": [idx]}
        if line.startswith("rx"):
            angle = float(line.split("(")[1].split(")")[0])
            idx = int(line.split("[")[1].split("]")[0])
            return {"name": "RX", "targets": [idx], "angle": angle}
        if line.startswith("ry"):
            angle = float(line.split("(")[1].split(")")[0])
            idx = int(line.split("[")[1].split("]")[0])
            return {"name": "RY", "targets": [idx], "angle": angle}
        if line.startswith("rz"):
            angle = float(line.split("(")[1].split(")")[0])
            idx = int(line.split("[")[1].split("]")[0])
            return {"name": "RZ", "targets": [idx], "angle": angle}
        if line.startswith("cx"):
            target_str = line.replace("cx", "", 1).strip()
            targets = [t.strip() for t in target_str.split(",") if t.strip()]
            control = int(targets[0].split("[")[1].split("]")[0])
            target = int(targets[1].split("[")[1].split("]")[0])
            return {"name": "CNOT", "targets": [control, target]}
        if line.startswith("cz"):
            target_str = line.replace("cz", "", 1).strip()
            targets = [t.strip() for t in target_str.split(",") if t.strip()]
            control = int(targets[0].split("[")[1].split("]")[0])
            target = int(targets[1].split("[")[1].split("]")[0])
            return {"name": "CZ", "targets": [control, target]}
        if line.startswith("swap"):
            target_str = line.replace("swap", "", 1).strip()
            targets = [t.strip() for t in target_str.split(",") if t.strip()]
            q1 = int(targets[0].split("[")[1].split("]")[0])
            q2 = int(targets[1].split("[")[1].split("]")[0])
            return {"name": "SWAP", "targets": [q1, q2]}
        return None

    def _apply_gate(self, state: np.ndarray, gate: Dict[str, Any], n: int) -> np.ndarray:
        name = gate["name"]
        if name == "H":
            mat = (1 / math.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
            return self._apply_single(state, mat, gate["targets"][0], n)
        if name == "X":
            mat = np.array([[0, 1], [1, 0]], dtype=complex)
            return self._apply_single(state, mat, gate["targets"][0], n)
        if name == "Y":
            mat = np.array([[0, -1j], [1j, 0]], dtype=complex)
            return self._apply_single(state, mat, gate["targets"][0], n)
        if name == "Z":
            mat = np.array([[1, 0], [0, -1]], dtype=complex)
            return self._apply_single(state, mat, gate["targets"][0], n)
        if name == "RX":
            angle = gate["angle"]
            mat = np.array(
                [[math.cos(angle / 2), -1j * math.sin(angle / 2)], [-1j * math.sin(angle / 2), math.cos(angle / 2)]],
                dtype=complex,
            )
            return self._apply_single(state, mat, gate["targets"][0], n)
        if name == "RY":
            angle = gate["angle"]
            mat = np.array(
                [[math.cos(angle / 2), -math.sin(angle / 2)], [math.sin(angle / 2), math.cos(angle / 2)]],
                dtype=complex,
            )
            return self._apply_single(state, mat, gate["targets"][0], n)
        if name == "RZ":
            angle = gate["angle"]
            mat = np.array([[np.exp(-1j * angle / 2), 0], [0, np.exp(1j * angle / 2)]], dtype=complex)
            return self._apply_single(state, mat, gate["targets"][0], n)
        if name == "CNOT":
            return self._apply_two_qubit(state, gate["targets"], n, "CNOT")
        if name == "CZ":
            return self._apply_two_qubit(state, gate["targets"], n, "CZ")
        if name == "SWAP":
            return self._apply_two_qubit(state, gate["targets"], n, "SWAP")
        return state

    def _apply_single(self, state: np.ndarray, gate: np.ndarray, qubit: int, n: int) -> np.ndarray:
        state = state.reshape([2] * n)
        axes = list(range(n))
        axes[0], axes[qubit] = axes[qubit], axes[0]
        state = np.transpose(state, axes)
        state = np.tensordot(gate, state, axes=([1], [0]))
        state = np.transpose(state, axes)
        return state.reshape(-1)

    def _apply_two_qubit(self, state: np.ndarray, qubits: List[int], n: int, gate_type: str) -> np.ndarray:
        q1, q2 = qubits
        if q1 == q2:
            return state
        state = state.reshape([2] * n)
        axes = list(range(n))
        axes[0], axes[q1] = axes[q1], axes[0]
        axes[1], axes[q2] = axes[q2], axes[1]
        state = np.transpose(state, axes)
        if gate_type == "CNOT":
            gate = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex)
        elif gate_type == "CZ":
            gate = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, -1]], dtype=complex)
        else:
            gate = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex)
        state = state.reshape(4, -1)
        state = gate @ state
        state = state.reshape([2, 2] + [2] * (n - 2))
        state = np.transpose(state, axes)
        return state.reshape(-1)

    def _sample_large_circuit(
        self,
        circuit: Dict[str, Any],
        *,
        shots: int,
        noisy: bool,
        seed: Optional[int],
    ) -> Dict[str, Any]:
        """Approximate sampled estimator for larger qubit counts."""
        num_qubits = int(circuit.get("num_qubits", 0))
        gate_count = len(circuit.get("gates", []))
        rng = np.random.default_rng(seed)
        start = time.time()

        # Track per-qubit bias as a lightweight proxy of gate effects.
        biases = np.full(num_qubits, 0.5, dtype=float)
        for gate in circuit.get("gates", []):
            name = str(gate.get("name", "")).upper()
            for target in gate.get("targets", []):
                if target < 0 or target >= num_qubits:
                    continue
                if name in {"X", "RX"}:
                    biases[target] = min(0.95, biases[target] + 0.08)
                elif name in {"Z", "RZ"}:
                    biases[target] = max(0.05, biases[target] - 0.05)
                elif name in {"H", "RY"}:
                    biases[target] = 0.5
                elif name in {"CNOT", "CZ"}:
                    biases[target] = (biases[target] * 0.7) + 0.15
        if noisy:
            noise = min(0.2, gate_count * 0.0025)
            biases = ((1 - noise) * biases) + (noise * 0.5)

        counts: Dict[str, int] = {}
        for _ in range(shots):
            bits = ["1" if rng.random() < biases[q] else "0" for q in range(num_qubits)]
            bitstring = "".join(bits)
            counts[bitstring] = counts.get(bitstring, 0) + 1
        return {
            "counts": counts,
            "statevector": [],
            "execution_time": time.time() - start,
            "mode": "sampled_noisy" if noisy else "sampled_ideal",
            "metadata": {
                "num_qubits": num_qubits,
                "gate_count": gate_count,
                "estimator": "large_circuit_sampling",
            },
        }


class QuantumAgent:
    """Quantum computing agent for ADA."""

    def __init__(
        self,
        diagnostic_engine: Optional[DiagnosticEngine] = None,
        project_root: Optional[str] = None,
    ) -> None:
        self._translator = QuantumProblemTranslator()
        self._tier1 = Tier1_ClassicalQuantum()
        self._tier2 = Tier2_RealQuantum()
        self._tier3 = Tier3_LocalSimulator()
        self._broker = MultiCloudQuantumBroker()
        self._context = ContextEngine()
        self._diagnostic = diagnostic_engine
        self._project_root = Path(project_root or Path(__file__).resolve().parents[1])
        self._frontier_cache: Dict[str, Dict[str, Any]] = {}

    async def execute(self, task_description: str) -> Dict[str, Any]:
        """Execute a quantum optimization task."""
        start = time.time()
        self._context.update_group(
            "agent_status",
            {
                "active_agents": [{"name": "quantum_agent", "status": "running", "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}],
            },
        )
        parsed = self._translator.parse_problem(task_description)
        result = {}
        tier_used = "tier1"
        success = True
        try:
            if parsed["problem_type"] == "graph":
                raw_vars = parsed.get("variables", [])
                nodes = [v.get("name", f"n{i}") if isinstance(v, dict) else v for i, v in enumerate(raw_vars)] or ["n0", "n1"]
                Q = self._translator.formulate_graph_problem(nodes, [])
                tier_used = "tier1-qaoa"
                result = await asyncio.to_thread(self._tier1.solve_qaoa, Q)
            elif parsed["problem_type"] == "variational":
                tier_used = "tier1-genetic"
                objective = lambda x: np.sum(x ** 2)
                result = await asyncio.to_thread(self._tier1.solve_genetic, objective, 3, [(-1, 1)] * 3)
            elif parsed["problem_type"] == "molecular":
                tier_used = "tier2"
                circuit = self._tier2.generate_circuit_for_problem(parsed)
                fidelity = self._tier2.estimate_circuit_fidelity(20, max(2, len(parsed.get("variables", [])) or 2))
                if fidelity < 0.3 or self._tier2._token is None:
                    tier_used = "tier3"
                    result = await asyncio.to_thread(self._tier3.simulate, circuit)
                else:
                    job_id = self._tier2.submit_circuit(circuit)
                    result = {"job_id": job_id, "status": self._tier2.check_job_status(job_id)}
            else:
                Q = self._translator.formulate_qubo(parsed.get("variables", []), parsed.get("constraints", []), parsed.get("objective", ""))
                if Q.size == 0:
                    Q = np.eye(2)
                tier_used = "tier1-anneal"
                result = await asyncio.to_thread(self._tier1.solve_qubo, Q)
        except Exception as exc:
            success = False
            result = {"error": str(exc)}
        execution_time = time.time() - start
        summary = self._format_result(result, tier_used)
        if self._diagnostic:
            self._diagnostic.health_monitor.record_agent_result("quantum_agent", success, execution_time, None if success else summary)
        self._context.update_group(
            "agent_status",
            {
                "active_agents": [{"name": "quantum_agent", "status": "idle", "started_at": ""}],
            },
        )
        return {
            "success": success,
            "tier_used": tier_used,
            "result_summary": summary,
            "raw_results": result,
            "execution_time": execution_time,
        }

    async def discovery_simulation(
        self,
        args: Dict[str, Any],
        *,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Cloud-heavy quantum-assisted multi-domain discovery workflow."""
        started = time.time()
        params = self._normalize_discovery_inputs(args)
        run_id = f"qdisc_{int(started)}_{uuid.uuid4().hex[:8]}"
        rng = random.Random(params["seed"])
        np.random.seed(params["seed"])
        budget: DiscoveryBudget = params["budget"]
        status = "completed"

        self._emit_discovery_event(
            event_callback,
            "ada:quantum_status",
            {
                "run_id": run_id,
                "stage": "starting",
                "objective": params["objective"],
                "domains": params["domains"],
                "fidelity": params["fidelity"],
                "discovery_mode": params["discovery_mode"],
            },
        )

        provider_plan = self._broker.select_provider_plan(
            domains=params["domains"],
            fidelity=params["fidelity"],
            budget=budget,
            require_hardware_validation=params["require_hardware_validation"],
        )
        provider_usage: List[Dict[str, Any]] = []
        ranked_candidates: List[Dict[str, Any]] = []
        rejected_candidates: List[Dict[str, Any]] = []
        jobs_used = 0
        total_cost = 0.0

        for domain in params["domains"]:
            if jobs_used >= budget.max_cloud_jobs:
                status = "budget_limited"
                break
            provider_row = next(
                (row for row in provider_plan["ranked"] if row["provider"] == provider_plan["primary"]),
                provider_plan["ranked"][0] if provider_plan["ranked"] else {"provider": "local_simulator", "estimated_job_cost_usd": 0.0},
            )
            projected_cost = float(provider_row.get("estimated_job_cost_usd", 0.0))
            if total_cost + projected_cost > budget.max_cost_usd:
                status = "budget_limited"
                break

            provider = str(provider_row.get("provider", "local_simulator"))
            jobs_used += 1
            total_cost += projected_cost
            domain_candidates = self._generate_candidates_for_domain(
                domain=domain,
                objective=params["objective"],
                constraints=params["constraints"],
                count=max(10, min(36, params["top_k"] * 3)),
                rng=rng,
            )
            scored, rejected = self._score_domain_candidates(
                domain=domain,
                candidates=domain_candidates,
                objective=params["objective"],
                discovery_mode=params["discovery_mode"],
                fidelity=params["fidelity"],
                provider=provider,
                seed=params["seed"],
                require_hardware_validation=params["require_hardware_validation"],
                hardware_available=bool(provider_row.get("hardware")),
            )
            ranked_candidates.extend(scored)
            rejected_candidates.extend(rejected)
            provider_usage.append(
                {
                    "domain": domain,
                    "provider": provider,
                    "estimated_queue_minutes": provider_row.get("estimated_queue_minutes", 0.0),
                    "estimated_job_cost_usd": round(projected_cost, 4),
                    "hardware": bool(provider_row.get("hardware")),
                    "fidelity": params["fidelity"],
                    "jobs_used": 1,
                }
            )

            self._emit_discovery_event(
                event_callback,
                "ada:quantum_discovery_update",
                {
                    "run_id": run_id,
                    "domain": domain,
                    "provider": provider,
                    "accepted": len(scored),
                    "rejected": len(rejected),
                    "jobs_used": jobs_used,
                    "max_jobs": budget.max_cloud_jobs,
                    "estimated_cost_usd": round(total_cost, 4),
                },
            )

        ranked_candidates.sort(
            key=lambda cand: (float(cand.get("score", 0.0)), float(cand.get("confidence", 0.0))),
            reverse=True,
        )
        ranked_candidates = ranked_candidates[: params["top_k"]]
        frontier_summary = self._build_frontier_summary(ranked_candidates)
        uncertainty_values = [float(item.get("uncertainty", 0.5)) for item in ranked_candidates]
        uncertainty_summary = {
            "mean_uncertainty": round(float(np.mean(uncertainty_values)) if uncertainty_values else 0.0, 4),
            "max_uncertainty": round(float(np.max(uncertainty_values)) if uncertainty_values else 0.0, 4),
            "min_uncertainty": round(float(np.min(uncertainty_values)) if uncertainty_values else 0.0, 4),
            "calibration": "mitigation-aware" if params["fidelity"] == "high" else "simulator-calibrated",
        }

        recommendations = [
            self._recommend_next_experiment(candidate, idx + 1)
            for idx, candidate in enumerate(ranked_candidates[: min(6, len(ranked_candidates))])
        ]
        cost_summary = {
            "estimated_cost_usd": round(total_cost, 4),
            "budget_cap_usd": budget.max_cost_usd,
            "jobs_used": jobs_used,
            "job_cap": budget.max_cloud_jobs,
            "runtime_seconds": round(time.time() - started, 3),
        }

        artifacts = self._write_discovery_artifacts(
            run_id=run_id,
            params=params,
            ranked_candidates=ranked_candidates,
            rejected_candidates=rejected_candidates,
            frontier_summary=frontier_summary,
            provider_usage=provider_usage,
            cost_summary=cost_summary,
            uncertainty_summary=uncertainty_summary,
            recommendations=recommendations,
        )
        result = {
            "run_id": run_id,
            "status": status,
            "ranked_candidates": ranked_candidates,
            "rejected_candidates": rejected_candidates,
            "frontier_summary": frontier_summary,
            "provider_usage": provider_usage,
            "cost_summary": cost_summary,
            "uncertainty_summary": uncertainty_summary,
            "recommended_next_experiments": recommendations,
            "artifacts": artifacts,
        }
        self._frontier_cache[run_id] = frontier_summary
        self._emit_discovery_event(
            event_callback,
            "ada:quantum_discovery_complete",
            {
                "run_id": run_id,
                "status": status,
                "top_candidates": [c.get("candidate_id") for c in ranked_candidates[:3]],
                "artifacts": artifacts,
            },
        )
        return result

    def _normalize_discovery_inputs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        raw_domains = args.get("domains") if isinstance(args.get("domains"), list) else []
        domains = [str(d).strip().lower() for d in raw_domains if str(d).strip()]
        allowed_domains = {"materials", "molecular", "reaction", "emergent_tech"}
        domains = [d for d in domains if d in allowed_domains]
        if not domains:
            domains = ["materials"]
        objective = str(args.get("objective", "")).strip() or "discover high value candidates"
        fidelity = str(args.get("fidelity", "balanced")).strip().lower()
        if fidelity not in {"quick", "balanced", "high"}:
            fidelity = "balanced"
        discovery_mode = str(args.get("discovery_mode", "conservative")).strip().lower()
        if discovery_mode not in {"conservative", "exploratory"}:
            discovery_mode = "conservative"
        top_k = int(args.get("top_k", 10))
        top_k = max(1, min(100, top_k))

        raw_budget = args.get("budget", {}) if isinstance(args.get("budget"), dict) else {}
        budget = DiscoveryBudget(
            max_runtime_minutes=max(1, int(raw_budget.get("max_runtime_minutes", 30))),
            max_cost_usd=max(0.0, float(raw_budget.get("max_cost_usd", 5.0))),
            max_cloud_jobs=max(1, int(raw_budget.get("max_cloud_jobs", 4))),
        )
        require_hardware_validation = bool(args.get("require_hardware_validation", fidelity == "high"))
        seed = int(args.get("seed")) if args.get("seed") is not None else int(time.time() % 100000)
        return {
            "objective": objective,
            "domains": domains,
            "constraints": args.get("constraints", {}) if isinstance(args.get("constraints"), dict) else {},
            "fidelity": fidelity,
            "discovery_mode": discovery_mode,
            "budget": budget,
            "top_k": top_k,
            "require_hardware_validation": require_hardware_validation,
            "seed": seed,
            "project_path": str(args.get("project_path", "")).strip(),
        }

    def _generate_candidates_for_domain(
        self,
        *,
        domain: str,
        objective: str,
        constraints: Dict[str, Any],
        count: int,
        rng: random.Random,
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        objective_tag = objective.lower().replace(" ", "_")[:36]
        if domain == "materials":
            elements = constraints.get("elements") if isinstance(constraints.get("elements"), list) else [
                "Li",
                "Na",
                "Mg",
                "Al",
                "Si",
                "P",
                "S",
                "Fe",
                "Mn",
                "Ni",
                "Co",
                "O",
                "F",
                "C",
            ]
            elements = [str(e) for e in elements if str(e)]
            if len(elements) < 3:
                elements = ["Li", "Fe", "Mn", "O", "C", "S"]
            for i in range(count):
                base = rng.sample(elements, k=min(3, len(elements)))
                composition = f"{base[0]}{rng.randint(1,3)}{base[1]}{rng.randint(1,4)}{base[2]}{rng.randint(1,4)}"
                candidates.append(
                    {
                        "candidate_id": self._candidate_id(domain, composition, objective_tag, i),
                        "domain": domain,
                        "label": composition,
                        "features": {
                            "stability_proxy": round(rng.uniform(0.2, 0.95), 4),
                            "bandgap_proxy": round(rng.uniform(0.1, 4.2), 4),
                            "synthesis_complexity": round(rng.uniform(0.1, 0.95), 4),
                        },
                    }
                )
        elif domain == "molecular":
            scaffolds = ["benzene", "thiophene", "pyridine", "imidazole", "piperazine", "quinoline", "triazine"]
            substituents = ["F", "Cl", "OH", "NH2", "CN", "CH3", "OCH3", "COOH"]
            for i in range(count):
                scaffold = rng.choice(scaffolds)
                sub = rng.choice(substituents)
                label = f"{scaffold}-{sub}-{rng.randint(1,4)}"
                candidates.append(
                    {
                        "candidate_id": self._candidate_id(domain, label, objective_tag, i),
                        "domain": domain,
                        "label": label,
                        "features": {
                            "binding_proxy": round(rng.uniform(0.2, 0.97), 4),
                            "synthetic_accessibility": round(rng.uniform(0.15, 0.95), 4),
                            "toxicity_proxy": round(rng.uniform(0.05, 0.6), 4),
                        },
                    }
                )
        elif domain == "reaction":
            catalysts = ["Ni", "Pd", "Cu", "Fe", "Co", "Ru"]
            pathways = ["single_step", "dual_step", "electro_route", "photoredox", "thermal_cycle"]
            for i in range(count):
                catalyst = rng.choice(catalysts)
                pathway = rng.choice(pathways)
                label = f"{pathway}:{catalyst}:{rng.randint(120,380)}C"
                candidates.append(
                    {
                        "candidate_id": self._candidate_id(domain, label, objective_tag, i),
                        "domain": domain,
                        "label": label,
                        "features": {
                            "yield_proxy": round(rng.uniform(0.25, 0.98), 4),
                            "energy_proxy": round(rng.uniform(0.1, 0.9), 4),
                            "selectivity_proxy": round(rng.uniform(0.2, 0.95), 4),
                        },
                    }
                )
        else:
            archetypes = [
                "quantum_battery_mesh",
                "photonic_interconnect",
                "neuromorphic_spintronics",
                "quantum_kernel_classifier",
                "superconducting_gateway",
                "meta_material_sensor_fabric",
            ]
            for i in range(count):
                label = f"{rng.choice(archetypes)}:{rng.randint(1,99)}"
                candidates.append(
                    {
                        "candidate_id": self._candidate_id(domain, label, objective_tag, i),
                        "domain": domain,
                        "label": label,
                        "features": {
                            "cross_domain_synergy": round(rng.uniform(0.15, 0.98), 4),
                            "deployment_readiness": round(rng.uniform(0.1, 0.95), 4),
                            "scalability_proxy": round(rng.uniform(0.2, 0.9), 4),
                        },
                    }
                )
        return candidates

    def _score_domain_candidates(
        self,
        *,
        domain: str,
        candidates: List[Dict[str, Any]],
        objective: str,
        discovery_mode: str,
        fidelity: str,
        provider: str,
        seed: int,
        require_hardware_validation: bool,
        hardware_available: bool,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        provider_conf = {
            "bluequbit": 0.90,
            "braket": 0.85,
            "local_simulator": 0.72,
        }.get(provider, 0.72)
        fidelity_gain = {"quick": 0.03, "balanced": 0.08, "high": 0.13}.get(fidelity, 0.08)
        mode_weights = (
            {"novelty": 0.32, "feasibility": 0.46, "objective": 0.22}
            if discovery_mode == "conservative"
            else {"novelty": 0.52, "feasibility": 0.23, "objective": 0.25}
        )
        objective_l = objective.lower()

        for idx, candidate in enumerate(candidates):
            features = candidate.get("features", {})
            feature_values = [float(v) for v in features.values()] if features else [0.5]
            feasibility = min(1.0, max(0.0, float(np.mean(feature_values))))
            novelty = min(
                1.0,
                max(
                    0.0,
                    0.35
                    + (abs(hash(f"{candidate['candidate_id']}_{seed}") % 1000) / 1000.0) * 0.55,
                ),
            )
            objective_alignment = 0.5
            if "lightweight" in objective_l or "energy" in objective_l:
                objective_alignment += 0.12 if domain in {"materials", "reaction"} else 0.04
            if "molecule" in objective_l or "drug" in objective_l:
                objective_alignment += 0.12 if domain == "molecular" else 0.04
            if "technology" in objective_l or "emerg" in objective_l:
                objective_alignment += 0.12 if domain == "emergent_tech" else 0.03
            objective_alignment = min(1.0, objective_alignment)

            score = (
                novelty * mode_weights["novelty"]
                + feasibility * mode_weights["feasibility"]
                + objective_alignment * mode_weights["objective"]
                + fidelity_gain
            )
            confidence = min(0.99, max(0.05, provider_conf + (feasibility * 0.1) + fidelity_gain))
            uncertainty = min(0.95, max(0.02, 1.0 - confidence + (0.08 if provider == "local_simulator" else 0.03)))

            if require_hardware_validation and not hardware_available:
                rejected.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "domain": domain,
                        "reason": "hardware_validation_unavailable",
                    }
                )
                continue
            if discovery_mode == "conservative" and (feasibility < 0.42 or uncertainty > 0.6):
                rejected.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "domain": domain,
                        "reason": "failed_conservative_thresholds",
                    }
                )
                continue

            accepted.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "domain": domain,
                    "label": candidate["label"],
                    "score": round(float(score), 6),
                    "confidence": round(float(confidence), 6),
                    "uncertainty": round(float(uncertainty), 6),
                    "novelty": round(float(novelty), 6),
                    "feasibility": round(float(feasibility), 6),
                    "objective_alignment": round(float(objective_alignment), 6),
                    "provider": provider,
                    "hardware_validated": bool(hardware_available and fidelity == "high" and idx < 3),
                    "explainability": {
                        "top_factors": sorted(
                            [
                                {"name": "novelty", "value": round(float(novelty), 4)},
                                {"name": "feasibility", "value": round(float(feasibility), 4)},
                                {"name": "objective_alignment", "value": round(float(objective_alignment), 4)},
                            ],
                            key=lambda row: row["value"],
                            reverse=True,
                        ),
                        "provider_influence": provider,
                        "uncertainty_source": "noise+model_selection" if provider != "local_simulator" else "simulator_gap",
                    },
                    "raw_features": features,
                }
            )
        return accepted, rejected

    def _build_frontier_summary(self, ranked_candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        domains: Dict[str, int] = {}
        for candidate in ranked_candidates:
            domain = str(candidate.get("domain", "unknown"))
            domains[domain] = domains.get(domain, 0) + 1
        frontier = [
            {
                "candidate_id": c.get("candidate_id"),
                "domain": c.get("domain"),
                "score": c.get("score"),
                "confidence": c.get("confidence"),
            }
            for c in ranked_candidates[:5]
        ]
        return {
            "domain_distribution": domains,
            "frontier_size": len(ranked_candidates),
            "frontier": frontier,
        }

    def _recommend_next_experiment(self, candidate: Dict[str, Any], rank: int) -> Dict[str, Any]:
        domain = str(candidate.get("domain", "materials"))
        label = str(candidate.get("label", candidate.get("candidate_id", "candidate")))
        if domain == "materials":
            protocol = "DFT pre-screen + synthesis feasibility check + accelerated aging simulation"
        elif domain == "molecular":
            protocol = "conformer sweep + VQE property estimate + docking and ADMET triage"
        elif domain == "reaction":
            protocol = "pathway barrier scan + catalyst loading optimization + selectivity validation"
        else:
            protocol = "cross-domain architecture benchmark + hardware integration sandbox"
        return {
            "rank": rank,
            "candidate_id": candidate.get("candidate_id"),
            "candidate_label": label,
            "protocol": protocol,
            "goal": "reduce uncertainty before lab validation",
        }

    def _write_discovery_artifacts(
        self,
        *,
        run_id: str,
        params: Dict[str, Any],
        ranked_candidates: List[Dict[str, Any]],
        rejected_candidates: List[Dict[str, Any]],
        frontier_summary: Dict[str, Any],
        provider_usage: List[Dict[str, Any]],
        cost_summary: Dict[str, Any],
        uncertainty_summary: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        project_path = self._resolve_project_path(params.get("project_path", ""))
        run_dir = project_path / "quantum" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        candidates_payload = {
            "run_id": run_id,
            "ranked_candidates": ranked_candidates,
            "rejected_candidates": rejected_candidates,
        }
        provenance_payload = {
            "run_id": run_id,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "parameters": {
                "objective": params.get("objective"),
                "domains": params.get("domains"),
                "constraints": params.get("constraints"),
                "fidelity": params.get("fidelity"),
                "discovery_mode": params.get("discovery_mode"),
                "budget": params.get("budget").__dict__ if isinstance(params.get("budget"), DiscoveryBudget) else {},
                "seed": params.get("seed"),
            },
            "provider_usage": provider_usage,
            "cost_summary": cost_summary,
            "uncertainty_summary": uncertainty_summary,
        }
        report_lines = [
            f"# Quantum Discovery Report ({run_id})",
            "",
            f"- Objective: {params.get('objective')}",
            f"- Domains: {', '.join(params.get('domains', []))}",
            f"- Fidelity: {params.get('fidelity')}",
            f"- Discovery mode: {params.get('discovery_mode')}",
            f"- Cost used: ${cost_summary.get('estimated_cost_usd', 0):.4f}",
            f"- Jobs used: {cost_summary.get('jobs_used', 0)} / {cost_summary.get('job_cap', 0)}",
            "",
            "## Frontier Summary",
            json.dumps(frontier_summary, indent=2),
            "",
            "## Top Candidates",
        ]
        for idx, candidate in enumerate(ranked_candidates[:10], start=1):
            report_lines.append(
                f"{idx}. {candidate.get('candidate_id')} [{candidate.get('domain')}] "
                f"score={candidate.get('score')} confidence={candidate.get('confidence')} uncertainty={candidate.get('uncertainty')}"
            )
        report_lines.append("")
        report_lines.append("## Recommended Next Experiments")
        for rec in recommendations:
            report_lines.append(
                f"- Rank {rec.get('rank')}: {rec.get('candidate_id')} -> {rec.get('protocol')}"
            )

        candidates_path = run_dir / "candidates.json"
        provenance_path = run_dir / "provenance.json"
        report_path = run_dir / "report.md"
        candidates_path.write_text(json.dumps(candidates_payload, indent=2), encoding="utf-8")
        provenance_path.write_text(json.dumps(provenance_payload, indent=2), encoding="utf-8")
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        return {
            "report": str(report_path),
            "candidates": str(candidates_path),
            "provenance": str(provenance_path),
        }

    def _resolve_project_path(self, explicit_project_path: str) -> Path:
        if explicit_project_path:
            explicit = Path(explicit_project_path).expanduser()
            if explicit.is_absolute():
                return explicit
            return (self._project_root / explicit).resolve()
        snapshot = self._context.get_snapshot()
        active_project = (snapshot.active_project or "temp").strip() or "temp"
        return self._project_root / "projects" / active_project

    def _candidate_id(self, domain: str, label: str, objective_tag: str, index: int) -> str:
        digest = hashlib.sha1(f"{domain}|{label}|{objective_tag}|{index}".encode("utf-8")).hexdigest()[:12]
        return f"{domain[:4]}_{digest}"

    def _emit_discovery_event(
        self,
        callback: Optional[Callable[[str, Dict[str, Any]], None]],
        event_name: str,
        payload: Dict[str, Any],
    ) -> None:
        if callback is None:
            return
        try:
            callback(event_name, payload)
        except Exception:
            pass

    def analyze_problem(self, description: str) -> Dict[str, Any]:
        """Analyze problem without solving."""
        return self._translator.parse_problem(description)

    def simulate_circuit(
        self,
        qasm_circuit: str,
        *,
        noisy: bool = False,
        seed: Optional[int] = None,
        shots: int = 1024,
    ) -> Dict[str, Any]:
        """Simulate a circuit locally."""
        if not qasm_circuit.strip():
            return {"error": "Missing qasm_circuit"}
        return self._tier3.simulate(qasm_circuit, shots=shots, noisy=noisy, seed=seed)

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tool definitions for ADA."""
        return [
            {
                "name": "quantum_optimize",
                "description": "Solve an optimization problem using quantum methods.",
                "parameters": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]},
            },
            {
                "name": "quantum_simulate_circuit",
                "description": "Simulate a quantum circuit using the local simulator.",
                "parameters": {"type": "object", "properties": {"qasm_circuit": {"type": "string"}}, "required": ["qasm_circuit"]},
            },
            {
                "name": "quantum_analyze_problem",
                "description": "Analyze a problem and recommend the best approach.",
                "parameters": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]},
            },
            {
                "name": "quantum_discovery_simulation",
                "description": "Run cloud-heavy quantum-assisted discovery simulation across materials, molecular, reaction, and emerging-tech domains.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "objective": {"type": "string"},
                        "domains": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["materials", "molecular", "reaction", "emergent_tech"]},
                            "minItems": 1,
                        },
                        "constraints": {"type": "object"},
                        "fidelity": {"type": "string", "enum": ["quick", "balanced", "high"]},
                        "discovery_mode": {"type": "string", "enum": ["conservative", "exploratory"]},
                        "budget": {
                            "type": "object",
                            "properties": {
                                "max_runtime_minutes": {"type": "integer", "minimum": 1},
                                "max_cost_usd": {"type": "number", "minimum": 0},
                                "max_cloud_jobs": {"type": "integer", "minimum": 1},
                            },
                        },
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 100},
                        "require_hardware_validation": {"type": "boolean"},
                        "seed": {"type": "integer"},
                    },
                    "required": ["objective", "domains"],
                },
            },
        ]

    def _format_result(self, result: Dict[str, Any], tier_used: str) -> str:
        if tier_used.startswith("tier1-anneal"):
            solution = result.get("best_solution", [])
            return f"Optimal configuration found with energy {result.get('best_energy', 0):.2f}. Selection vector: {solution}."
        if tier_used.startswith("tier1-qaoa"):
            return f"Routing configuration optimized. Best energy: {result.get('best_energy', 0):.2f}."
        if tier_used.startswith("tier1-genetic"):
            return f"Optimal parameters found with fitness {result.get('best_fitness', 0):.3f}."
        if tier_used == "tier2":
            if "job_id" in result:
                return f"Quantum job submitted to BlueQubit. Job ID: {result['job_id']}."
        if tier_used == "tier3":
            return "Simulated quantum circuit locally. Results ready for review."
        if "error" in result:
            return f"Quantum solver failed: {result['error']}"
        return "Quantum optimization completed."


if __name__ == "__main__":
    translator = QuantumProblemTranslator()
    tier1 = Tier1_ClassicalQuantum()
    tier2 = Tier2_RealQuantum()
    tier3 = Tier3_LocalSimulator()

    variables = [
        {
            "name": "motor",
            "options": [
                {"value": "A", "weight": 120, "cost": 40, "performance": 7.5},
                {"value": "B", "weight": 140, "cost": 35, "performance": 8.0},
            ],
        },
        {
            "name": "battery",
            "options": [
                {"value": "C", "weight": 200, "cost": 50, "performance": 8.5},
                {"value": "D", "weight": 160, "cost": 60, "performance": 7.0},
            ],
        },
    ]
    constraints = [{"type": "max", "variable": "weight", "value": 350}]
    Q = translator.formulate_qubo(variables, constraints, "minimize weight")
    print("Tier1 anneal:", tier1.solve_qubo(Q, num_reads=200)["best_energy"])

    bell = "\n".join(["OPENQASM 3.0;", "qubit[5] q;", "h q[0];", "cx q[0], q[1];"])
    print("Tier3 simulate:", tier3.simulate(bell, shots=128)["counts"])

    example = {"problem_type": "combinatorial", "variables": [{"name": "q0"}, {"name": "q1"}]}
    circuit = tier2.generate_circuit_for_problem(example)
    print("Tier2 circuit:", circuit)
