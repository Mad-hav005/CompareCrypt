"""
Exact private matching orchestrator.
"""

from typing import List, Tuple
from app.crypto.psi import OPRFExactPSI
from app.utils.normalization import normalize_dataset


class ExactMatcher:
    """
    Orchestrates exact private set intersection between Alice and Bob.
    Ensures input normalization while maintaining privacy separation.
    """

    def __init__(self) -> None:
        self.psi_protocol = OPRFExactPSI()

    def match(
        self,
        alice_data: List[str],
        bob_data: List[str],
        normalize: bool = True,
    ) -> Tuple[List[str], int, int]:
        """
        Executes exact private matching.

        Args:
            alice_data: Alice's dataset.
            bob_data: Bob's dataset.
            normalize: Whether to apply canonical string normalization.

        Returns:
            Tuple of (matches, alice_unique_count, bob_unique_count).
        """
        if normalize:
            alice_items = normalize_dataset(alice_data)
            bob_items = normalize_dataset(bob_data)
        else:
            alice_items = list(dict.fromkeys(alice_data))
            bob_items = list(dict.fromkeys(bob_data))

        matches = self.psi_protocol.run_protocol(alice_items, bob_items)
        return matches, len(alice_items), len(bob_items)
