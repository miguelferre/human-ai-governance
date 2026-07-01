"""Mapeo de las guidelines HAX/PAIR a marco normativo (EU AI Act / NIST AI RMF).

Convierte un hallazgo atado a guidelines en su situacion regulatoria: que
articulos del AI Act y que subcategorias del NIST AI RMF toca. El objetivo es que
el informe sirva como *evidencia de conformidad* para el comprador de gobernanza,
no solo como critica de diseno academica.

Los datos viven en guidelines/regulatory_map.yaml. Es un mapeo ORIENTATIVO, no un
dictamen legal (ver ADR-008 y el aviso del propio YAML).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import yaml

from interaction_review.guidelines import guidelines_by_id
from interaction_review.schemas import Finding

_MAP_FILE = Path(__file__).parent / "guidelines" / "regulatory_map.yaml"

# Orden de presentacion de los marcos.
FRAMEWORKS: tuple[str, ...] = ("eu_ai_act", "nist_ai_rmf")


@lru_cache(maxsize=1)
def _raw() -> dict:
    return yaml.safe_load(_MAP_FILE.read_text(encoding="utf-8"))


def framework_names() -> dict[str, str]:
    """id de framework -> nombre legible."""
    fw = _raw()["frameworks"]
    return {k: fw[k]["name"] for k in FRAMEWORKS}


def _ref_sort_key(ref: str) -> tuple[str, int, str]:
    """Ordena refs: por prefijo textual y primer numero (Art. 9 antes que Art. 13)."""
    m = re.search(r"\d+", ref)
    if m:
        return (ref[: m.start()].strip(), int(m.group()), ref)
    return (ref, 9999, ref)  # caracteristicas sin numero: al final de su prefijo


def refs_for(guideline_ids: Iterable[str]) -> dict[str, list[str]]:
    """Union de refs normativos por framework para un conjunto de guidelines.

    Devuelve solo los frameworks con al menos un ref. Ignora ids desconocidos.
    """
    m = _raw()["map"]
    acc: dict[str, set[str]] = {fw: set() for fw in FRAMEWORKS}
    for gid in guideline_ids:
        entry = m.get(gid)
        if not entry:
            continue
        for fw in FRAMEWORKS:
            acc[fw].update(entry.get(fw, []))
    return {fw: sorted(acc[fw], key=_ref_sort_key) for fw in FRAMEWORKS if acc[fw]}


def crosswalk(findings: list[Finding]) -> dict[str, list[tuple[str, list[str]]]]:
    """Por framework: cada ref -> las guidelines (citadas por los hallazgos) que lo implican.

    Es la vista de 'evidencia de conformidad': que requisitos regulatorios tocan los
    hallazgos del informe y por que guideline.
    """
    m = _raw()["map"]
    per_fw: dict[str, dict[str, set[str]]] = {fw: {} for fw in FRAMEWORKS}
    for f in findings:
        for gid in f.guideline_ids:
            entry = m.get(gid)
            if not entry:
                continue
            for fw in FRAMEWORKS:
                for ref in entry.get(fw, []):
                    per_fw[fw].setdefault(ref, set()).add(gid)
    out: dict[str, list[tuple[str, list[str]]]] = {}
    for fw in FRAMEWORKS:
        if not per_fw[fw]:
            continue
        items = [(ref, sorted(gids)) for ref, gids in per_fw[fw].items()]
        items.sort(key=lambda t: _ref_sort_key(t[0]))
        out[fw] = items
    return out


def unmapped_guidelines() -> list[str]:
    """Guidelines reales que NO tienen entrada en el mapa (debe ser vacio: todas mapeadas)."""
    mapped = set(_raw()["map"])
    real = set(guidelines_by_id())
    return sorted(real - mapped)


def unknown_map_ids() -> list[str]:
    """Ids del mapa que no corresponden a ninguna guideline real (erratas)."""
    mapped = set(_raw()["map"])
    real = set(guidelines_by_id())
    return sorted(mapped - real)
