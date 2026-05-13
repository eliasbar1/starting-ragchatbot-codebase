import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Up to 2 sequential searches per query** — use a second search only when the first result is insufficient to answer the question
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to 2 sequential tool-call rounds.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]

        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        response = self.client.messages.create(**api_params)

        if not tools or not tool_manager:
            return response.content[0].text

        MAX_ROUNDS = 2
        for round_num in range(MAX_ROUNDS):
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            if not tool_use_blocks:
                break

            messages.append({"role": "assistant", "content": response.content})
            tool_results = self._handle_tool_execution(response.content, tool_manager)
            messages.append({"role": "user", "content": tool_results})

            if round_num < MAX_ROUNDS - 1:
                # Intermediate call: with tools so Claude can decide to search again
                response = self.client.messages.create(**{
                    **self.base_params,
                    "messages": messages,
                    "system": system_content,
                    "tools": tools,
                    "tool_choice": {"type": "auto"}
                })
            else:
                # Round limit reached: synthesis call without tools
                response = self.client.messages.create(**{
                    **self.base_params,
                    "messages": messages,
                    "system": system_content
                })

        return response.content[0].text

    def _handle_tool_execution(self, response_content: List, tool_manager) -> List[Dict]:
        """
        Execute all tool calls from a response and return tool result dicts.

        Args:
            response_content: Content blocks from an assistant response
            tool_manager: Manager to execute tools

        Returns:
            List of tool_result dicts (one per tool_use block)
        """
        tool_results = []
        for block in response_content:
            if block.type != "tool_use":
                continue
            try:
                result = tool_manager.execute_tool(block.name, **block.input)
            except Exception as e:
                result = f"Tool execution error: {e}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result
            })
        return tool_results
