"""Native PySide6 desktop interface for FracVAL."""


def launch() -> int:
    """Launch the FracVAL Qt desktop application."""
    from .main import main
    return main()


__all__ = ["launch"]
