from __future__ import annotations


class TrainingAssistantError(Exception):
    """Base exception for the training assistant bot."""


class StorageError(TrainingAssistantError):
    """Errors related to persistent storage operations."""


class ValidationError(TrainingAssistantError):
    """Validation related errors raised when user data is inconsistent."""


class OpenAIError(TrainingAssistantError):
    """Wrapper for OpenAI integration issues."""
