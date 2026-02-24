#!/usr/bin/env python3
"""
bloch_sphere_rotation.py
────────────────────────
Rotate a single qubit by an arbitrary angle around an arbitrary axis,
using the basis gate set:  Hadamard (H) · Phase (S) · Pi/8 (T) · CNOT (CX).

Usage
-----
    python bloch_sphere_rotation.py [input_file.yaml]

If no file is given, 'rotation_params.yaml' in the same directory is used.

Input file keys (YAML)
----------------------
    angle          : rotation angle (float)
    unit           : 'radians' (default) or 'degrees'
    axis           : [nx, ny, nz]  – will be normalised
    amplitude_zero : real amplitude α of |0⟩ so that |ψ⟩ = α|0⟩ + √(1-α²)|1⟩

Output
------
    circuit_rotation.png       – transpiled gate circuit diagram
    bloch_sphere_rotation.png  – Bloch-sphere visualisation (before / after)
"""

import sys
import os
import numpy as np
import yaml
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401  (registers 3D projection)
import matplotlib.gridspec as gridspec
from matplotlib.image import imread

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import UnitaryGate

# ── directory of THIS script (for default file lookup) ──────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))


# ────────────────────────────────────────────────────────────────────────────
#  Physics helpers
# ────────────────────────────────────────────────────────────────────────────

def prepare_state(alpha: float) -> np.ndarray:
    """
    Build the qubit state vector from the |0⟩ amplitude α.
    Returns  [α, √(1-α²)]  (real, normalised).
    """
    alpha = float(alpha)
    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"amplitude_zero must be in [0, 1]; got {alpha}")
    return np.array([alpha, np.sqrt(max(0.0, 1.0 - alpha**2))], dtype=complex)


def rotation_unitary(angle: float, axis: np.ndarray) -> np.ndarray:
    """
    SU(2) rotation matrix:  R_n(θ) = cos(θ/2)·I − i·sin(θ/2)·(n·σ)
    where σ = (X, Y, Z) are the Pauli matrices and n is a unit vector.
    """
    axis = np.asarray(axis, dtype=float)
    norm = np.linalg.norm(axis)
    if norm < 1e-12:
        raise ValueError("Rotation axis cannot be the zero vector.")
    axis /= norm
    nx, ny, nz = axis
    c, s = np.cos(angle / 2), np.sin(angle / 2)
    return np.array([
        [c - 1j*s*nz,        -s*(ny + 1j*nx)],
        [ s*(ny - 1j*nx),     c + 1j*s*nz   ]
    ], dtype=complex)


def bloch_vector(sv: np.ndarray) -> np.ndarray:
    """Convert 2-component state vector to Bloch-sphere coordinates (x, y, z)."""
    a, b = sv[0], sv[1]
    return np.array([
        2.0 * float(np.real(np.conj(a) * b)),
        2.0 * float(np.imag(np.conj(a) * b)),
        float(abs(a)**2 - abs(b)**2)
    ])


# ────────────────────────────────────────────────────────────────────────────
#  Bloch-sphere drawing
# ────────────────────────────────────────────────────────────────────────────

def _draw_bloch(ax, vectors, colors, labels, title: str):
    """
    Render a Bloch sphere on a 3-D Axes with one or more state vectors.

    Parameters
    ----------
    vectors : list of array-like, shape (3,)
    colors  : list of colour strings
    labels  : list of legend labels (use '' to suppress)
    title   : subplot title
    """
    # Transparent unit sphere
    theta = np.linspace(0, np.pi, 40)
    phi   = np.linspace(0, 2*np.pi, 80)
    X = np.outer(np.sin(theta), np.cos(phi))
    Y = np.outer(np.sin(theta), np.sin(phi))
    Z = np.outer(np.cos(theta), np.ones_like(phi))
    ax.plot_surface(X, Y, Z, alpha=0.07, color='lightblue', zorder=0)
    ax.plot_wireframe(X, Y, Z, alpha=0.10, color='steelblue',
                      linewidth=0.35, rstride=4, cstride=8)

    # Coordinate axes + pole labels
    for d, lbl in zip([[1,0,0],[0,1,0],[0,0,1]], ['x','y','z']):
        ax.quiver(0, 0, 0, *d, length=1.3, color='dimgray',
                  alpha=0.5, arrow_length_ratio=0.08, linewidth=0.8)
        ax.text(d[0]*1.5, d[1]*1.5, d[2]*1.5, lbl,
                fontsize=9, color='dimgray', ha='center')
    ax.text(0, 0,  1.18, '|0⟩', fontsize=9, ha='center', color='black')
    ax.text(0, 0, -1.28, '|1⟩', fontsize=9, ha='center', color='black')

    # State / axis vectors
    for v, c, l in zip(vectors, colors, labels):
        v = np.asarray(v, dtype=float)
        ax.quiver(0, 0, 0, v[0], v[1], v[2],
                  color=c, linewidth=2.5, arrow_length_ratio=0.15,
                  label=l if l else None)

    ax.set_xlim([-1.5, 1.5]); ax.set_ylim([-1.5, 1.5]); ax.set_zlim([-1.5, 1.5])
    ax.set_box_aspect([1, 1, 1])
    ax.axis('off')
    ax.set_title(title, fontsize=10, pad=4)
    leg_labels = [l for l in labels if l]
    if leg_labels:
        ax.legend(fontsize=8, loc='upper right')


# ────────────────────────────────────────────────────────────────────────────
#  Main
# ────────────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Load parameters ───────────────────────────────────────────────────
    input_file = sys.argv[1] if len(sys.argv) > 1 \
        else os.path.join(_HERE, 'rotation_params.yaml')

    with open(input_file) as fh:
        p = yaml.safe_load(fh)

    angle  = float(p.get('angle', np.pi))
    unit   = str(p.get('unit', 'radians')).strip().lower()
    axis   = list(p.get('axis', [0, 0, 1]))
    alpha0 = float(p.get('amplitude_zero', 1.0))

    if unit in ('deg', 'degree', 'degrees'):
        angle = np.radians(angle)

    axis_arr = np.array(axis, dtype=float)
    axis_arr /= np.linalg.norm(axis_arr)

    # ── 2. Compute states ────────────────────────────────────────────────────
    psi_in  = prepare_state(alpha0)
    R       = rotation_unitary(angle, axis_arr)
    psi_out = R @ psi_in

    bv_in  = bloch_vector(psi_in)
    bv_out = bloch_vector(psi_out)

    def fmt_amp(c):
        """Format a complex amplitude as a neat string."""
        if abs(c.imag) < 1e-9:
            return f"{c.real:+.4f}"
        return f"({c.real:+.4f}{c.imag:+.4f}j)"

    print("=" * 58)
    print("  Bloch Sphere Rotation")
    print("=" * 58)
    print(f"  Angle   : {np.degrees(angle):.4f}°  ({angle:.6f} rad)")
    print(f"  Axis    : {np.round(axis_arr, 5)}")
    print(f"  |0⟩ amp : {alpha0:.4f}")
    print(f"  ψ_in    : {fmt_amp(psi_in[0])}|0⟩  {fmt_amp(psi_in[1])}|1⟩")
    print(f"  ψ_out   : {fmt_amp(psi_out[0])}|0⟩  {fmt_amp(psi_out[1])}|1⟩")
    print(f"  Bloch in  : {np.round(bv_in,  5)}")
    print(f"  Bloch out : {np.round(bv_out, 5)}")

    # ── 3. Build & transpile the rotation circuit ────────────────────────────
    qc = QuantumCircuit(1)
    rot_gate = UnitaryGate(R, label=f'Rₙ({np.degrees(angle):.1f}°)')
    qc.append(rot_gate, [0])

    # Basis: H, S (and its inverse S†), T (and its inverse T†), CNOT.
    # S† and T† are included because the KAK decomposer may need them;
    # they are expressible as S³ and T⁷ respectively (pure S/T sequences).
    basis = ['h', 't']
    qc_t  = transpile(qc, basis_gates=basis, optimization_level=3)

    ops = dict(qc_t.count_ops())
    print(f"\n  Transpiled depth : {qc_t.depth()}")
    print(f"  Gate counts      : {ops}")
    core = {k: v for k, v in ops.items() if k in basis}
    print(f"  Basis-gate counts: {core}")

    # ── 4. Save circuit diagram ──────────────────────────────────────────────
    circ_path = os.path.join(_HERE, 'circuit_rotation.png')
    circ_fig  = qc_t.draw('mpl', style='iqp', fold=40)
    circ_fig.savefig(circ_path, dpi=350, bbox_inches='tight')
    plt.close(circ_fig)
    print(f"\n  Saved: {circ_path}")

    # ── 5. Build Bloch-sphere figure ─────────────────────────────────────────
    fig = plt.figure(figsize=(15, 5.5))
    fig.patch.set_facecolor('#f8f8f8')
    fig.suptitle(
        f'R_n({np.degrees(angle):.2f}°)  |  '
        f'axis = {np.round(axis_arr, 3)}  |  '
        f'α₀ = {alpha0:.3f}',
        fontsize=13, fontweight='bold'
    )

    gs   = gridspec.GridSpec(1, 3, figure=fig, wspace=0.05)
    ax_l = fig.add_subplot(gs[0], projection='3d')
    ax_m = fig.add_subplot(gs[1], projection='3d')
    ax_r = fig.add_subplot(gs[2], projection='3d')

    _draw_bloch(
        ax_l,
        [bv_in],
        ['royalblue'],
        [f'{alpha0:.2f}|0⟩ + {psi_in[1].real:.2f}|1⟩'],
        'Input state  |ψ_in⟩'
    )
    _draw_bloch(
        ax_m,
        [bv_in, bv_out, axis_arr],
        ['royalblue', 'crimson', 'forestgreen'],
        ['|ψ_in⟩', '|ψ_out⟩', 'rot. axis n̂'],
        'Both states + rotation axis'
    )
    _draw_bloch(
        ax_r,
        [bv_out],
        ['crimson'],
        [f'|ψ_out⟩'],
        'Output state  |ψ_out⟩'
    )

    bloch_path = os.path.join(_HERE, 'bloch_sphere_rotation.png')
    fig.savefig(bloch_path, dpi=350, bbox_inches='tight')
    print(f"  Saved: {bloch_path}")

    # ── 6. Show both figures ─────────────────────────────────────────────────
    # Load the circuit image and show it in a second window
    circ_display = plt.figure(figsize=(12, 3))
    circ_display.patch.set_facecolor('#f8f8f8')
    ax_circ = circ_display.add_subplot(111)
    ax_circ.imshow(imread(circ_path))
    ax_circ.axis('off')
    ax_circ.set_title('Transpiled Rotation Circuit',
                      fontsize=8, pad=6)

    plt.show()


if __name__ == '__main__':
    main()
