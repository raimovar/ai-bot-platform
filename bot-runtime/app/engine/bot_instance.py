"""
Bot Instance - Single bot execution context.
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, Any
import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.factory import LLMFactory
from app.memory.manager import MemoryManager
from app.tools.registry import ToolRegistry


class BotInstance:
    """
    Single bot execution context.
    
    Handles:
    - Message processing
    - Context building
    - LLM calls
    - Tool execution
    - Response formatting
    """
    
    def __init__(
        self,
        bot_id: uuid.UUID,
        config: dict,
        db_session: AsyncSession,
        redis_client,
        ai_gateway_url: str,
    ):
        self.bot_id = bot_id
        self.config = config
        self.db = db_session
        self.redis = redis_client
        self.ai_gateway_url = ai_gateway_url
        
        # Initialize components
        self.llm = LLMFactory.create(
            provider=config.get("provider", "openai"),
            model=config.get("model_name", "gpt-4"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
        )
        
        self.memory = MemoryManager(
            redis=self.redis,
            bot_id=str(bot_id),
            memory_type=config.get("memory_type", "short_term"),
            memory_config=config.get("memory_config", {}),
        )
        
        self.tools = ToolRegistry.from_config(
            config.get("tools", [])
        )
        
        self.is_running = False
    
    async def start(self):
        """Start the bot instance."""
        self.is_running = True
        print(f"✅ Bot {self.bot_id} started")
    
    async def stop(self):
        """Stop the bot instance."""
        self.is_running = False
        print(f"👋 Bot {self.bot_id} stopped")
    
    async def process_message(
        self,
        message: str,
        session_id: uuid.UUID,
        user_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """
        Process a user message and return response.
        
        Steps:
        1. Build context (system prompt + memory + tools)
        2. Call LLM
        3. Execute tools if needed
        4. Update memory
        5. Return response
        """
        # Build context
        context = await self._build_context(session_id, user_name, user_id)
        
        # Add system prompt
        messages = [
            {"role": "system", "content": self.config.get("system_prompt", "")}
        ]
        
        # Add conversation history
        messages.extend(context.get("history", []))
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call LLM with tools
        llm_response = await self._call_llm(messages)
        
        # Update memory
        await self.memory.add_message("user", message, session_id)
        await self.memory.add_message("assistant", llm_response["content"], session_id)
        
        return llm_response
    
    async def _build_context(
        self,
        session_id: uuid.UUID,
        user_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Build context for LLM call."""
        # Get recent history from memory
        history = await self.memory.get_history(session_id)
        
        # Build context
        context = {
            "history": history,
            "user_name": user_name,
            "user_id": user_id,
        }
        
        # TODO: Add RAG context if knowledge base is configured
        
        return context
    
    async def _call_llm(self, messages: list[dict]) -> dict:
        """Call LLM through AI Gateway."""
        # Prepare request
        payload = {
            "messages": messages,
            "model": self.config.get("model_name", "gpt-4"),
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 2048),
        }
        
        # Add tools if configured
        if self.tools.has_tools():
            payload["tools"] = self.tools.get_definitions()
        
        # Call AI Gateway
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.ai_gateway_url}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
        
        # Extract response
        choice = result["choices"][0]
        message = choice["message"]
        
        # Check for tool calls
        if message.get("tool_calls"):
            # Execute tools and continue
            result = await self._handle_tool_calls(messages, message)
        else:
            result = {
                "content": message["content"],
                "model": result.get("model", "unknown"),
                "tokens_used": result.get("usage", {}).get("total_tokens", 0),
            }
        
        return result
    
    async def _handle_tool_calls(
        self,
        messages: list[dict],
        assistant_message: dict,
    ) -> dict:
        """Handle tool calls from LLM."""
        tool_calls = assistant_message.get("tool_calls", [])
        
        # Add assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": assistant_message["content"],
            "tool_calls": tool_calls,
        })
        
        # Execute each tool
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            
            # Execute tool
            result = await self.tools.execute(
                tool_name,
                tool_args,
                context={"bot_id": str(self.bot_id)}
            )
            
            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result),
            })
        
        # Continue with tool results
        return await self._call_llm(messages)
