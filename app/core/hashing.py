import hashlib
from typing import List


def deterministic_hash(user_id: str, experiment_id: str) -> float:
    """
    Produces a stable float in [0, 1) from user_id + experiment_id.
    Same inputs always yield same output — no randomness.
    """
    raw = f"{user_id}::{experiment_id}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    # Take first 8 hex chars → 32-bit integer → normalize to [0,1)
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket


def assign_variant(user_id: str, experiment_id: str, variant_names: List[str], weights: List[float]) -> str:
    """
    Given variant names and their allocation weights (must sum to ~1),
    deterministically assign a user to a variant.
    """
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError(f"Variant weights must sum to 1.0, got {sum(weights)}")

    bucket = deterministic_hash(user_id, experiment_id)
    cumulative = 0.0
    for name, weight in zip(variant_names, weights):
        cumulative += weight
        if bucket < cumulative:
            return name

    return variant_names[-1]  # fallback for floating point edge cases
