from mcp_sql_agent.app.interfaces.mcp.tools import sql_tools

mcp = sql_tools.mcp


def start_mcp():
    # Default to stdio for MCP clients; switch to http for REST-style access.
    mcp.run(transport="stdio")
