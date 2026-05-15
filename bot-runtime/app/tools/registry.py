"""
Tool Registry - Manages bot tools/functions.
"""
import json
from typing import Optional, Callable, Any
import httpx


class BaseTool:
    """Base class for tools."""
    
    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.config = config or {}
    
    async def execute(self, args: dict, context: dict) -> Any:
        """Execute the tool."""
        raise NotImplementedError
    
    def get_definition(self) -> dict:
        """Get OpenAI function definition."""
        raise NotImplementedError


class HttpTool(BaseTool):
    """HTTP request tool."""
    
    async def execute(self, args: dict, context: dict) -> Any:
        """Execute HTTP request."""
        url = args.get("url")
        method = args.get("method", "GET").upper()
        headers = args.get("headers", {})
        body = args.get("body")
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=body,
                timeout=30.0,
            )
            return {
                "status": response.status_code,
                "body": response.text[:5000],  # Truncate
            }
    
    def get_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.config.get("description", "Make HTTP request"),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                        "headers": {"type": "object"},
                        "body": {"type": "object"},
                    },
                    "required": ["url"],
                },
            },
        }


class CommandTool(BaseTool):
    """Shell command execution tool (sandboxed)."""
    
    async def execute(self, args: dict, context: dict) -> Any:
        """Execute shell command (limited)."""
        import subprocess
        
        cmd = args.get("command", "")
        
        # Security: limit commands
        allowed = ["ping", "curl", "echo"]
        if not any(cmd.startswith(a) for a in allowed):
            return {"error": "Command not allowed"}
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Execute a limited shell command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                    },
                    "required": ["command"],
                },
            },
        }


class ToolRegistry:
    """Registry for bot tools."""
    
    _tool_types = {
        "http": HttpTool,
        "command": CommandTool,
    }
    
    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
    
    @classmethod
    def from_config(cls, tools_config: list[dict]) -> "ToolRegistry":
        """Create registry from configuration."""
        registry = cls()
        
        for tool_config in tools_config:
            tool_type = tool_config.get("type", "http")
            tool_class = cls._tool_types.get(tool_type, HttpTool)
            
            tool = tool_class(
                name=tool_config["name"],
                config=tool_config.get("config", {}),
            )
            
            registry.register(tool)
        
        return registry
    
    def register(self, tool: BaseTool):
        """Register a tool."""
        self.tools[tool.name] = tool
    
    def has_tools(self) -> bool:
        """Check if any tools are registered."""
        return len(self.tools) > 0
    
    def get_definitions(self) -> list[dict]:
        """Get all tool definitions."""
        return [tool.get_definition() for tool in self.tools.values()]
    
    async def execute(
        self,
        tool_name: str,
        args: dict,
        context: dict,
    ) -> Any:
        """Execute a tool by name."""
        tool = self.tools.get(tool_name)
        
        if not tool:
            return {"error": f"Tool not found: {tool_name}"}
        
        try:
            return await tool.execute(args, context)
        except Exception as e:
            return {"error": str(e)}
    
    @classmethod
    def register_type(cls, name: str, tool_class: type):
        """Register a new tool type."""
        cls._tool_types[name] = tool_class
