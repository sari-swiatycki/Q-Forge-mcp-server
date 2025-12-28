from MCP.tools import sql_tools

mcp = sql_tools.mcp

def start_mcp():
    # מפעיל MCP על stdin/stdout או על HTTP
    mcp.run(transport="stdio")  # או "http" אם את רוצה REST API
