"""Entry point for `python -m cue`."""

from cue.server import mcp

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
