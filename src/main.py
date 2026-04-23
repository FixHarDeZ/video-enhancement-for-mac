"""Entry point for Video Enhancer."""

import platform
import sys


def _check_platform() -> None:
    if platform.system() != "Darwin":
        print("Error: This application requires macOS (Apple Silicon).", file=sys.stderr)
        sys.exit(1)

    machine = platform.machine()
    if machine != "arm64":
        print(
            f"Warning: This app is optimised for Apple Silicon (arm64). "
            f"Detected: {machine}. VideoToolbox hardware encoding may not be available.",
            file=sys.stderr,
        )


def main() -> None:
    _check_platform()

    # Import here so platform check runs first
    from src.app import VideoEnhancerApp  # noqa: PLC0415

    app = VideoEnhancerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
