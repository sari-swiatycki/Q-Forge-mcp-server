from MCP.mcp_server import mcp

def main():
    # הפעלת MCP
    mcp.run(transport="stdio")  # או "http"

if __name__ == "__main__":
    main()
