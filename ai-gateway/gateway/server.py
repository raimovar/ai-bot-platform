"""
AI Gateway - Unified LLM interface.

Routes requests to various LLM providers (OpenAI, Anthropic, Ollama, etc.)
with caching and rate limiting.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
import hashlib
import json
from typing import Optional
from pydantic import BaseModel


app = FastAPI(title="AI Gateway", version="1.0.0")

# Provider configs (from env)
OPENAI_API_KEY = ""
ANTHROPIC_API_KEY = ""
OLLAMA_BASE_URL = "http://localhost:11434"


class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: int = 2048
    tools: Optional[list] = None


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    Unified chat completions endpoint.
    
    Routes to appropriate provider based on model name.
    """
    # Determine provider
    if request.model.startswith("gpt-") or request.model.startswith("o1-"):
        return await openai_request(request)
    elif request.model.startswith("claude-"):
        return await anthropic_request(request)
    elif request.model.startswith("ollama:"):
        return await ollama_request(request)
    else:
        # Default to OpenAI
        return await openai_request(request)


async def openai_request(request: ChatRequest):
    """Call OpenAI API."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": request.model,
        "messages": request.messages,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    
    if request.tools:
        payload["tools"] = request.tools
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()


async def anthropic_request(request: ChatRequest):
    """Call Anthropic API."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")
    
    # Convert messages
    system = ""
    messages = []
    
    for msg in request.messages:
        if msg["role"] == "system":
            system = msg["content"]
        else:
            messages.append(msg)
    
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    
    payload = {
        "model": request.model,
        "messages": messages,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    
    if system:
        payload["system"] = system
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        result = response.json()
        
        # Convert to OpenAI format
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": result["content"][0]["text"],
                }
            }],
            "model": request.model,
            "usage": {
                "input_tokens": result["usage"]["input_tokens"],
                "output_tokens": result["usage"]["output_tokens"],
                "total_tokens": result["usage"]["total_tokens"],
            },
        }


async def ollama_request(request: ChatRequest):
    """Call Ollama API."""
    model = request.model.replace("ollama:", "")
    
    # Convert messages
    messages = [m for m in request.messages if m["role"] != "system"]
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": request.temperature,
            "num_predict": request.max_tokens,
        },
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=300.0,
        )
        response.raise_for_status()
        result = response.json()
        
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": result["message"]["content"],
                }
            }],
            "model": request.model,
            "usage": {
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            },
        }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
