#!/usr/bin/env python3
"""
two_level_decomp.py — Decompose a unitary matrix into 2-level unitaries.

Usage:
    python two_level_decomp.py <matrix_file> [--no-plot] [--output <file.png>]

Input file formats supported:
  • .npy         — NumPy binary array
  • .json / JSON — nested array (real or complex)
  • plain text   — one row per line, space-separated Python complex literals
                   (e.g.  "0.5+0.5j  0.5-0.5j")
                   or math "i"-notation (e.g. "1+2i" → treated as "1+2j")

A 2-level unitary is an n×n matrix that equals the identity except in a
2×2 submatrix at rows/columns {i, j}.  Every unitary can be written as a
finite product of 2-level unitaries (Nielsen & Chuang, §4.5.1).


# Example:
# Format: one row per line, space-separated Python complex literals (a+b0.5*j)
0.5   0.5   0.5   0.5
0.5   0.5j  -0.5  -0.5j
0.5  -0.5   0.5  -0.5
0.5  -0.5j  -0.5   0.5j


"""

import sys
import json
import ast
import argparse
import colorsys
from collections import namedtuple

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec


# ── Input parsing ─────────────────────────────────────────────────────────────

def parse_matrix(filename: str) -> np.ndarray:
    """Read a (possibly complex) square matrix from *filename*."""
    if filename.endswith(".npy"):
        return np.load(filename).astype(complex)

    with open(filename) as fh:
        text = fh.read().strip()

    # JSON
    try:
        return np.array(json.loads(text), dtype=complex)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # Python literal list-of-lists
    try:
        return np.array(ast.literal_eval(text), dtype=complex)
    except Exception:
        pass

    # Plain-text rows (math "i" → Python "j")
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.replace(",", " ").split()
        row = []
        for tok in tokens:
            tok = tok.replace("i", "j")
            try:
                row.append(complex(tok))
            except ValueError:
                raise ValueError(f"Cannot parse token: {tok!r}")
        rows.append(row)
    return np.array(rows, dtype=complex)


# ── Core algorithm ────────────────────────────────────────────────────────────

Factor = namedtuple("Factor", ["i", "j", "block", "matrix"])


def _apply_left(cur: np.ndarray, r: int, s: int, blk: np.ndarray) -> None:
    """In-place: replace rows r,s of *cur* with blk @ [row_r; row_s]."""
    rows = cur[[r, s], :].copy()
    cur[r, :] = blk[0, 0] * rows[0] + blk[0, 1] * rows[1]
    cur[s, :] = blk[1, 0] * rows[0] + blk[1, 1] * rows[1]


def _embed(n: int, r: int, s: int, blk: np.ndarray) -> np.ndarray:
    """Return the n×n identity with *blk* placed at rows/cols (r, s)."""
    M = np.eye(n, dtype=complex)
    M[r, r] = blk[0, 0]; M[r, s] = blk[0, 1]
    M[s, r] = blk[1, 0]; M[s, s] = blk[1, 1]
    return M


def decompose(U: np.ndarray, tol: float = 1e-12) -> list:
    """
    Decompose unitary U into 2-level unitaries.

    Algorithm (cf. Nielsen & Chuang §4.5.1):
      Repeatedly apply 2-level "Givens-like" rotations on the left to
      reduce U column-by-column to the identity.

      If  Mₖ ··· M₁ U = I  then  U = M₁† M₂† ··· Mₖ†,
      where each Mᵢ† is itself a 2-level unitary.

    Returns:
      List of Factor(i, j, block, matrix) in multiplication order, i.e.
        factors[0].matrix @ factors[1].matrix @ ··· ≈ U
    """
    n = U.shape[0]
    cur = U.copy().astype(complex)
    applied = []  # (r, s, blk) of each Mᵢ applied on the left

    for col in range(n - 1):
        # Zero out cur[row, col] for row = n-1 down to col+1
        for row in range(n - 1, col, -1):
            a = cur[row - 1, col]
            b = cur[row,     col]
            if abs(b) < tol:
                continue

            if abs(a) < tol:
                # a = 0, b ≠ 0 → swap rows so the nonzero entry moves up
                blk = np.array([[0, 1], [1, 0]], dtype=complex)
            else:
                # Givens rotation: V [a; b] = [√(|a|²+|b|²); 0]
                r_norm = np.hypot(abs(a), abs(b))
                blk = np.array(
                    [[a.conj() / r_norm,  b.conj() / r_norm],
                     [-b       / r_norm,  a        / r_norm]],
                    dtype=complex,
                )

            _apply_left(cur, row - 1, row, blk)
            applied.append((row - 1, row, blk))

        # cur[col, col] is now a pure phase e^(iφ); correct it
        phi = cur[col, col]
        if abs(phi - 1.0) > tol:
            blk = np.array([[phi.conj(), 0.0], [0.0, 1.0]], dtype=complex)
            cur[col, :] *= phi.conj()
            applied.append((col, col + 1, blk))

    # Handle the last diagonal element (may carry a residual phase)
    phi = cur[n - 1, n - 1]
    if abs(phi - 1.0) > tol:
        blk = np.array([[1.0, 0.0], [0.0, phi.conj()]], dtype=complex)
        cur[n - 1, :] *= phi.conj()
        applied.append((n - 2, n - 1, blk))

    # Build U = M₁† M₂† ··· Mₖ†  (each Mᵢ† is the inverse 2-level block)
    # Skip blocks that are numerically the identity (trivial factors).
    eye2 = np.eye(2, dtype=complex)
    factors = []
    for (r, s, blk) in applied:
        inv_blk = blk.conj().T
        if np.allclose(inv_blk, eye2, atol=tol):
            continue
        factors.append(Factor(r, s, inv_blk, _embed(n, r, s, inv_blk)))

    return factors


# ── Text output ───────────────────────────────────────────────────────────────

def _fmt_z(z: complex, width: int = 10) -> str:
    if abs(z.imag) < 1e-10:
        return f"{z.real:{width}.4f}"
    if abs(z.real) < 1e-10:
        return f"{z.imag:{width}.4f}i"
    sign = "+" if z.imag >= 0 else ""
    return f"({z.real:.3f}{sign}{z.imag:.3f}i)"


def print_decomposition(U: np.ndarray, factors: list) -> None:
    n  = U.shape[0]
    k  = len(factors)
    hr = "─" * 62

    print(f"\n{hr}")
    print(f"  Two-Level Unitary Decomposition   ({n}×{n}  →  {k} factors)")
    print(hr)
    print(f"\n  U =\n")
    for row in U:
        print("    " + "  ".join(_fmt_z(z) for z in row))

    print(f"\n  Decomposition:  U = V₁ · V₂ · … · V{k}\n")

    for idx, f in enumerate(factors):
        label = f"V{idx+1}"
        print(f"  {'─'*52}")
        print(f"  {label}  (acts on basis indices  i={f.i},  j={f.j})")
        print(f"     2×2 block:")
        for row in f.block:
            print("       " + "   ".join(_fmt_z(z, 9) for z in row))
        print()

    # Verification
    product = np.eye(n, dtype=complex)
    for f in factors:
        product = product @ f.matrix
    err = np.linalg.norm(product - U, ord="fro")
    print(hr)
    print(f"  Verification:  ‖V₁ · V₂ · … · V{k} − U‖_F  =  {err:.2e}")
    status = "✓  correct" if err < 1e-4 else "✗  WARNING — large residual!"
    print(f"  {status}")
    print(hr)


# ── Visualization ─────────────────────────────────────────────────────────────

def _rgba(z: complex, max_mag: float = 1.0):
    """Complex number → RGBA: hue encodes phase, value encodes magnitude."""
    mag = abs(z)
    if mag < 1e-12:
        return (0.90, 0.90, 0.90, 1.0)
    hue = (np.angle(z) / (2 * np.pi)) % 1.0
    val = 0.35 + 0.65 * min(mag / max_mag, 1.0)
    r, g, b = colorsys.hsv_to_rgb(hue, 0.80, val)
    return (r, g, b, 1.0)


def _draw_matrix(ax, M: np.ndarray, title: str,
                 active: tuple | None = None, tol: float = 1e-10) -> None:
    n       = M.shape[0]
    max_mag = max(abs(M).max(), 1e-12)
    fs      = max(5, 8 - n)          # font size shrinks for large matrices

    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(n - 0.5, -0.5)       # row 0 at top
    ax.set_aspect("equal")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([str(k) for k in range(n)], fontsize=6)
    ax.set_yticklabels([str(k) for k in range(n)], fontsize=6)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_linewidth(0.6)

    for i in range(n):
        for j in range(n):
            z    = M[i, j]
            rect = mpatches.FancyBboxPatch(
                (j - 0.47, i - 0.47), 0.94, 0.94,
                boxstyle="round,pad=0.04",
                facecolor=_rgba(z, max_mag),
                edgecolor="#555", linewidth=0.3,
            )
            ax.add_patch(rect)

            if abs(z) > tol:
                re, im = z.real, z.imag
                if abs(im) < tol:
                    txt = f"{re:.2f}"
                elif abs(re) < tol:
                    txt = f"{im:.2f}i"
                else:
                    sign = "+" if im > 0 else "−"
                    txt  = f"{re:.1f}\n{sign}{abs(im):.1f}i"
                ax.text(j, i, txt, ha="center", va="center",
                        fontsize=fs, color="#111", fontweight="bold",
                        linespacing=1.1)

    # Highlight rows & cols where the 2-level acts
    if active is not None:
        for idx in active:
            ax.axhline(idx, color="#e74c3c", lw=1.5, alpha=0.55, zorder=6)
            ax.axvline(idx, color="#e74c3c", lw=1.5, alpha=0.55, zorder=6)

    ax.set_title(title, fontsize=8.5, pad=4, fontweight="bold", color="#1a1a2e")


def _colorbar_legend(fig):
    """Add a small HSV phase-colour legend to the figure."""
    ax_cb = fig.add_axes([0.91, 0.12, 0.015, 0.30])
    phases = np.linspace(-np.pi, np.pi, 256)
    cdata  = np.array([[colorsys.hsv_to_rgb((p / (2 * np.pi)) % 1.0, 0.80, 0.75)]
                        for p in phases])
    ax_cb.imshow(cdata[::-1], aspect="auto", extent=[0, 1, -np.pi, np.pi])
    ax_cb.set_xticks([])
    ax_cb.set_yticks([-np.pi, 0, np.pi])
    ax_cb.set_yticklabels(["−π", "0", "+π"], fontsize=7)
    ax_cb.yaxis.set_label_position("right")
    ax_cb.yaxis.tick_right()
    ax_cb.set_title("phase", fontsize=7)


def visualize(U: np.ndarray, factors: list, output_file: str | None = None) -> None:
    n     = U.shape[0]
    k     = len(factors)
    total = k + 2          # U  +  k factors  +  product check

    ncols = min(total, 5)
    nrows = (total + ncols - 1) // ncols

    fig = plt.figure(figsize=(3.6 * ncols + 0.8, 3.9 * nrows + 1.0))
    fig.patch.set_facecolor("#f0f2f5")

    gs   = GridSpec(nrows, ncols, figure=fig,
                    hspace=0.55, wspace=0.38,
                    left=0.04, right=0.90,
                    top=0.88,  bottom=0.05)
    axes = [fig.add_subplot(gs[r, c])
            for r in range(nrows) for c in range(ncols)]

    # ── Panel 0: input U
    _draw_matrix(axes[0], U, "U  (input)")

    # ── Panels 1…k: each 2-level factor
    for idx, f in enumerate(factors):
        _draw_matrix(
            axes[idx + 1], f.matrix,
            f"V{idx+1}   {{{f.i},{f.j}}}",
            active=(f.i, f.j),
        )

    # ── Panel k+1: product verification
    product = np.eye(n, dtype=complex)
    for f in factors:
        product = product @ f.matrix
    err = np.linalg.norm(product - U, ord="fro")
    _draw_matrix(
        axes[k + 1], product,
        f"V₁ ··· V{k}  (product)\n‖P−U‖ = {err:.1e}",
    )

    # Hide leftover axes
    for idx in range(k + 2, len(axes)):
        axes[idx].set_visible(False)

    # Equation line
    eq = "U = " + " · ".join(f"V{i+1}" for i in range(k))
    fig.suptitle(
        f"Two-Level Unitary Decomposition   ({n}×{n}  →  {k} factors)\n{eq}",
        fontsize=11, fontweight="bold", y=0.97, color="#1a1a2e",
    )

    _colorbar_legend(fig)

    if output_file:
        fig.savefig(output_file, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"  Figure saved → {output_file}")
    else:
        plt.show()

    plt.close(fig)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="Decompose a unitary matrix into 2-level unitaries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("matrix_file",
                   help="File containing the unitary matrix (see formats above)")
    p.add_argument("--no-plot", action="store_true",
                   help="Skip the graphical visualisation")
    p.add_argument("--output", metavar="FILE",
                   help="Save the figure to FILE instead of displaying it")
    args = p.parse_args()

    print(f"Reading matrix from {args.matrix_file!r} …")
    U = parse_matrix(args.matrix_file)

    n = U.shape[0]
    if U.ndim != 2 or U.shape[1] != n:
        sys.exit("Error: matrix must be square.")
    print(f"  Shape: {n}×{n}")

    err_unit = np.linalg.norm(U @ U.conj().T - np.eye(n), ord="fro")
    if err_unit > 1e-4:
        print(f"  WARNING: matrix may not be unitary  (‖UU†−I‖ = {err_unit:.2e})")
    else:
        print(f"  ✓  Unitary  (‖UU†−I‖ = {err_unit:.2e})")

    print("Decomposing …")
    factors = decompose(U)
    print(f"  {len(factors)} 2-level factors found.")

    print_decomposition(U, factors)

    if not args.no_plot:
        print("\nRendering visualisation …")
        visualize(U, factors, output_file=args.output)


if __name__ == "__main__":
    main()
