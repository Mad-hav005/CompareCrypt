"""
Abstract interfaces for cryptographic primitives used in Private Set Intersection.

Decouples the high-level protocol and matching services from the underlying
cryptographic constructions, allowing clean replacement with alternative groups
or curves (e.g., NIST P-256, Curve25519, or Paillier/HE) without breaking consumers.
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Any


class BaseGroup(ABC):
    """
    Abstract interface for a cryptographic cyclic group of prime order.
    """

    @property
    @abstractmethod
    def order(self) -> int:
        """Returns the order of the subgroup."""
        pass

    @abstractmethod
    def hash_to_group(self, data: str) -> Any:
        """
        Deterministically maps a string to a valid non-identity element in the group.
        """
        pass

    @abstractmethod
    def exponentiate(self, base: Any, exponent: int) -> Any:
        """Computes base^exponent in the group."""
        pass

    @abstractmethod
    def inverse_scalar(self, scalar: int) -> int:
        """Computes scalar^{-1} modulo the subgroup order."""
        pass

    @abstractmethod
    def random_scalar(self) -> int:
        """Generates a cryptographically secure random non-zero scalar in [2, order-1]."""
        pass


class BaseOPRFClient(ABC):
    """
    Abstract interface for the client in an Oblivious Pseudorandom Function (OPRF).
    """

    @abstractmethod
    def blind(self, input_item: str) -> Tuple[Any, int]:
        """
        Blinds an input item using a freshly generated secret blinding scalar.

        Args:
            input_item: The plaintext string element.

        Returns:
            A tuple of (blinded_element, blinding_scalar).
        """
        pass

    @abstractmethod
    def finalize(self, input_item: str, evaluated_element: Any, blinding_scalar: int) -> bytes:
        """
        Unblinds the server's evaluation and hashes to obtain the OPRF output.

        Args:
            input_item: Original plaintext string element.
            evaluated_element: The element returned by the server.
            blinding_scalar: The secret scalar used during blinding.

        Returns:
            The finalized pseudorandom OPRF output as bytes.
        """
        pass


class BaseOPRFServer(ABC):
    """
    Abstract interface for the server in an Oblivious Pseudorandom Function (OPRF).
    """

    @property
    @abstractmethod
    def key(self) -> int:
        """Returns the server's secret scalar key."""
        pass

    @abstractmethod
    def evaluate(self, blinded_element: Any) -> Any:
        """
        Evaluates the OPRF on a client's blinded element using the server's secret key.

        Args:
            blinded_element: The blinded group element from the client.

        Returns:
            The evaluated group element.
        """
        pass

    @abstractmethod
    def evaluate_direct(self, input_item: str) -> bytes:
        """
        Directly computes the OPRF on a plaintext item using the server's secret key.

        Args:
            input_item: Plaintext string element from the server's own dataset.

        Returns:
            The finalized pseudorandom OPRF output as bytes.
        """
        pass


class BasePSIProtocol(ABC):
    """
    Abstract interface for a Private Set Intersection protocol.
    """

    @abstractmethod
    def run_protocol(self, client_items: List[str], server_items: List[str]) -> List[str]:
        """
        Executes the PSI protocol between a client and server, returning
        the exact matching elements known to the client.

        Args:
            client_items: Client's private dataset.
            server_items: Server's private dataset.

        Returns:
            List of matching plaintext items.
        """
        pass
