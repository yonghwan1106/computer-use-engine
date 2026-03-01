"""Entry point for `python -m cue`."""

from cue.server import init, mcp


def main():
    init()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
