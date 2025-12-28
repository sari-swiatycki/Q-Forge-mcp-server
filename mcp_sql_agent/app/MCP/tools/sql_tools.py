from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sql")

@mcp.tool()
async def run_query(nl_query: str, execute: bool = False) -> str:
    """
    Dummy tool to test MCP + LLM connection.
    
    Args:
        nl_query: Query in natural language
        execute: If True, actually execute (we won't yet)
    """
    # כאן נחזיר SQL פיקטיבי
    sql_query = f"SELECT * FROM users WHERE name LIKE '%{nl_query}%';"

    # נחזיר גם את ה-SQL וגם תוצאה מדומה
    fake_result = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    
    if execute:
        return f"Executed SQL: {sql_query}\nResults: {fake_result}"
    
    return f"SQL query: {sql_query}\nResults: {fake_result}"



@mcp.tool()
async def ping() -> str:
    """Health check tool."""
    return "pong"

