"""
Deterministic local mock reply provider with identifier screening; no external inference.
"""
from typing import Dict, Any, Optional
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Opentrons Liquid Handler Agent"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return f"[{self.system_name} Mock]: No external language model was invoked. Input received: {prompt[:60]!r}. This is not a scientific or protocol validation."


class LLMFactory:
    """Creates configured LLM client instances with zero-PHI protection."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Opentrons Liquid Handler Agent"):
        prov = str(provider).lower()
        if prov in ["mock", "deterministic", "test"]:
            return MockLLM(system_name)
        raise ValueError(f"Model provider {provider!r} is not implemented; use mock for deterministic local queries.")
