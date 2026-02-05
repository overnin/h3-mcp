from __future__ import annotations

from ..models.schemas import (
    H3CompareManyInput,
    H3CompareManyOutput,
    H3CompareSetsInput,
    H3CompareSetsOutput,
    OverlapCellset,
    OverlapPair,
    SetStats,
)
from .cellsets import resolve_cellset, store_cellset


def h3_compare_sets(payload: H3CompareSetsInput) -> H3CompareSetsOutput:
    cells_a = resolve_cellset(payload.set_a.cellset)
    cells_b = resolve_cellset(payload.set_b.cellset)
    set_a = set(cells_a)
    set_b = set(cells_b)
    overlap = set_a & set_b
    only_a = set_a - set_b
    only_b = set_b - set_a

    set_a_count = len(set_a)
    set_b_count = len(set_b)
    overlap_count = len(overlap)
    only_a_count = len(only_a)
    only_b_count = len(only_b)
    union_count = set_a_count + set_b_count - overlap_count

    overlap_ratio_a = overlap_count / set_a_count if set_a_count else 0.0
    overlap_ratio_b = overlap_count / set_b_count if set_b_count else 0.0
    jaccard_index = overlap_count / union_count if union_count else 0.0

    overlap_cellset_id = store_cellset(sorted(overlap)) if overlap_count else None
    only_a_cellset_id = store_cellset(sorted(only_a)) if only_a_count else None
    only_b_cellset_id = store_cellset(sorted(only_b)) if only_b_count else None

    overlap_cells = sorted(overlap) if payload.include_cells else None
    only_a_cells = sorted(only_a) if payload.include_cells else None
    only_b_cells = sorted(only_b) if payload.include_cells else None

    summary = (
        f"{overlap_count} of {set_a_count} {payload.set_a.label} cells overlap with "
        f"{payload.set_b.label}. {only_b_count} of {set_b_count} "
        f"{payload.set_b.label} cells are exclusive."
    )

    return H3CompareSetsOutput(
        set_a_label=payload.set_a.label,
        set_b_label=payload.set_b.label,
        set_a_count=set_a_count,
        set_b_count=set_b_count,
        overlap_count=overlap_count,
        only_a_count=only_a_count,
        only_b_count=only_b_count,
        overlap_ratio_a=overlap_ratio_a,
        overlap_ratio_b=overlap_ratio_b,
        jaccard_index=jaccard_index,
        overlap_cellset_id=overlap_cellset_id,
        only_a_cellset_id=only_a_cellset_id,
        only_b_cellset_id=only_b_cellset_id,
        overlap_cells=overlap_cells,
        only_a_cells=only_a_cells,
        only_b_cells=only_b_cells,
        summary=summary,
    )


def h3_compare_many(payload: H3CompareManyInput) -> H3CompareManyOutput:
    labels: list[str] = []
    cell_sets: list[set[str]] = []
    set_stats: list[SetStats] = []

    for labeled in payload.sets:
        cells = resolve_cellset(labeled.cellset)
        labels.append(labeled.label)
        cell_sets.append(set(cells))
        set_stats.append(SetStats(label=labeled.label, cell_count=len(set(cells))))

    if len(set(labels)) != len(labels):
        raise ValueError("Set labels must be unique for h3_compare_many.")

    label_to_index = {label: idx for idx, label in enumerate(labels)}

    n = len(cell_sets)
    overlap_counts_matrix: list[list[int]] = []
    overlap_score_matrix: list[list[float]] = []

    overlap_pairs: list[OverlapPair] = []
    overlap_cellsets: list[OverlapCellset] | None = [] if payload.include_cells else None

    if payload.return_mode == "stats":
        overlap_counts_matrix = [[0 for _ in range(n)] for _ in range(n)]
        overlap_score_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            overlap_counts_matrix[i][i] = len(cell_sets[i])
            if payload.matrix_metric == "jaccard":
                overlap_score_matrix[i][i] = 1.0 if len(cell_sets[i]) else 0.0
            else:
                overlap_score_matrix[i][i] = 1.0 if len(cell_sets[i]) else 0.0

    for i in range(n):
        for j in range(i + 1, n):
            overlap = cell_sets[i] & cell_sets[j]
            overlap_count = len(overlap)

            if payload.return_mode == "stats":
                overlap_counts_matrix[i][j] = overlap_counts_matrix[j][i] = overlap_count
                if payload.matrix_metric == "jaccard":
                    union_count = len(cell_sets[i]) + len(cell_sets[j]) - overlap_count
                    score = overlap_count / union_count if union_count else 0.0
                    overlap_score_matrix[i][j] = overlap_score_matrix[j][i] = score
                else:
                    a_score = overlap_count / len(cell_sets[i]) if len(cell_sets[i]) else 0.0
                    b_score = overlap_count / len(cell_sets[j]) if len(cell_sets[j]) else 0.0
                    overlap_score_matrix[i][j] = a_score
                    overlap_score_matrix[j][i] = b_score

            if overlap_count == 0:
                continue

            if payload.matrix_metric == "jaccard":
                union_count = len(cell_sets[i]) + len(cell_sets[j]) - overlap_count
                score = overlap_count / union_count if union_count else 0.0
                overlap_pairs.append(
                    OverlapPair(
                        a=labels[i],
                        b=labels[j],
                        overlap_count=overlap_count,
                        score=score,
                    )
                )
            else:
                a_score = overlap_count / len(cell_sets[i]) if len(cell_sets[i]) else 0.0
                b_score = overlap_count / len(cell_sets[j]) if len(cell_sets[j]) else 0.0
                overlap_pairs.append(
                    OverlapPair(
                        a=labels[i],
                        b=labels[j],
                        overlap_count=overlap_count,
                        score=a_score,
                    )
                )
                overlap_pairs.append(
                    OverlapPair(
                        a=labels[j],
                        b=labels[i],
                        overlap_count=overlap_count,
                        score=b_score,
                    )
                )

    overlap_pairs.sort(key=lambda pair: (pair.score, pair.overlap_count), reverse=True)
    top_overlaps = overlap_pairs[: payload.top_k]

    if not top_overlaps:
        summary = "No overlaps between sets."
    else:
        summary = (
            f"Strongest overlap: {top_overlaps[0].a} vs {top_overlaps[0].b} "
            f"({payload.matrix_metric} {top_overlaps[0].score:.2f})."
        )

    if payload.include_cells:
        overlap_cellsets = []
        for pair in top_overlaps:
            overlap = cell_sets[label_to_index[pair.a]] & cell_sets[label_to_index[pair.b]]
            overlap_cellsets.append(
                OverlapCellset(
                    a=pair.a,
                    b=pair.b,
                    cellset_id=store_cellset(sorted(overlap)),
                )
            )

    overlap_counts: list[list[int]] | None = None
    overlap_matrix: list[list[float]] | None = None
    if payload.return_mode == "stats":
        overlap_counts = overlap_counts_matrix
        overlap_matrix = overlap_score_matrix

    return H3CompareManyOutput(
        set_stats=set_stats,
        overlap_counts=overlap_counts,
        overlap_matrix=overlap_matrix,
        top_overlaps=top_overlaps,
        overlap_cellsets=overlap_cellsets,
        summary=summary,
    )
