from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot import build_system_prompt

AGENT_PRESETS: dict[str, dict[str, str]] = {
    "nexo-fast": {
        "model": "openai/gpt-4o-mini",
        "desc": "Fast, general support replies.",
    },
    "claude-pro": {
        "model": "anthropic/claude-opus-4.1",
        "desc": "High quality reasoning and writing.",
    },
    "gemini-pro": {
        "model": "google/gemini-2.0-flash-001",
        "desc": "Fast + strong multimodal style reasoning.",
    },
    "coder": {
        "model": "deepseek/deepseek-r1",
        "desc": "Code-heavy tasks and debugging support.",
    },
    "coder-pro": {
        "model": "deepseek/deepseek-chat",
        "desc": "DeepSeek V4 Flash - excellent at all coding tasks.",
    },
}


async def _reply_chunked(interaction: discord.Interaction, text: str) -> None:
    if not text.strip():
        await interaction.followup.send("(empty response)")
        return

    lines = text.split("\n")
    chunks: list[str] = []
    current = ""
    in_code_block = False

    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block

        candidate = current + ("\n" if current else "") + line
        if len(candidate) > 1800:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate

    if current:
        chunks.append(current)

    if not chunks:
        await interaction.followup.send("(empty response)")
        return

    first_embed = discord.Embed(
        title="NexoAI Response",
        description=chunks[0][:4096],
        color=discord.Color.blurple(),
    )
    await interaction.followup.send(embed=first_embed)
    for chunk in chunks[1:]:
        await interaction.channel.send(chunk)  # type: ignore[union-attr]


class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _run_ai(
        self,
        interaction: discord.Interaction,
        user_text: str,
        instruction: str | None = None,
        temperature: float = 0.7,
        search_context: str | None = None,
        override_model: str | None = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        guild_id = interaction.guild.id if interaction.guild else 0
        system_prompt = await build_system_prompt(
            interaction.user.id, guild_id, interaction.guild, user_text
        )

        profile = await self.bot.db.get_user_profile(interaction.user.id)  # type: ignore[attr-defined]
        model_key = (profile.get("agent_model") or "").strip().lower()
        selected_model = override_model or AGENT_PRESETS.get(model_key, {}).get("model", self.bot.settings.openrouter_model)  # type: ignore[attr-defined]

        final_user_text = user_text
        if search_context:
            final_user_text = f"Based on web search results:\n{search_context}\n\nUser question:\n{user_text}"
        if instruction:
            final_user_text = f"{instruction}\n\n{final_user_text}"

        history = await self.bot.db.get_recent_messages(  # type: ignore[attr-defined]
            guild_id,
            interaction.channel_id,
            limit=self.bot.settings.history_limit,
        )
        messages = [{"role": "system", "content": system_prompt}, *history]
        messages.append({"role": "user", "content": final_user_text})

        try:
            response = await self.bot.llm.chat(  # type: ignore[attr-defined]
                messages,
                temperature=temperature,
                max_tokens=self.bot.settings.openrouter_max_tokens,
                model=selected_model,
            )
            await self.bot.memory.store_message(interaction.user.id, guild_id, interaction.channel_id, "user", final_user_text)  # type: ignore[attr-defined]
            await self.bot.memory.store_message(interaction.user.id, guild_id, interaction.channel_id, "assistant", response)  # type: ignore[attr-defined]
            await _reply_chunked(interaction, response)
        except RuntimeError as exc:
            error_text = str(exc)
            if "All providers failed" in error_text:
                await interaction.followup.send("All AI providers are currently unavailable. Please try again later.")
            else:
                await interaction.followup.send(f"AI request failed: `{error_text[:500]}`")
        except Exception:
            await interaction.followup.send("Something went wrong. Please try again in a moment.")

    @app_commands.command(name="ai", description="Ask AI anything.")
    async def ai(self, interaction: discord.Interaction, prompt: str) -> None:
        await self._run_ai(interaction, prompt)

    @app_commands.command(name="websearch", description="Search Google and get AI answer.")
    async def websearch(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(thinking=True)
        search_text = await self.bot.search.search(query)  # type: ignore[attr-defined]
        await self._run_ai(
            interaction,
            query,
            instruction="Answer based on the provided search results. Cite sources.",
            search_context=search_text,
        )

    IMAGE_SIZE_CHOICES = [
        app_commands.Choice(name="Square 1024x1024", value="1024x1024"),
        app_commands.Choice(name="Wide 1792x1024", value="1792x1024"),
        app_commands.Choice(name="Tall 1024x1792", value="1024x1792"),
    ]

    @app_commands.command(name="imagine", description="Generate an image from text.")
    @app_commands.describe(
        prompt="Describe the image you want to generate",
        model="Image model override (default from config)",
        size="Image size (DALL-E 3 only)",
        enhance="Auto-enhance your prompt for better results (default: True)",
        image_url="URL of image to vary or edit",
        mode="Generate, vary, or edit (default: generate)",
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Generate (new image)", value="generate"),
        app_commands.Choice(name="Variation (based on image)", value="variation"),
        app_commands.Choice(name="Edit (modify image)", value="edit"),
    ])
    async def imagine(
        self,
        interaction: discord.Interaction,
        prompt: str,
        model: str | None = None,
        size: str | None = None,
        enhance: bool = True,
        image_url: str | None = None,
        mode: str = "generate",
    ) -> None:
        await interaction.response.defer(thinking=True)
        gen_model = model or self.bot.settings.image_gen_model

        if image_url and mode in ("variation", "edit"):
            self.bot.image_gen.model = gen_model  # type: ignore[attr-defined]
            result = await self.bot.image_gen.generate(  # type: ignore[attr-defined]
                prompt, size=size, image_url=image_url, mode=mode
            )
        else:
            final_prompt = prompt
            if enhance:
                enhanced = await self.bot.image_gen.enhance_prompt(  # type: ignore[attr-defined]
                    prompt, self.bot.llm.chat  # type: ignore[attr-defined]
                )
                if enhanced:
                    final_prompt = enhanced

            self.bot.image_gen.model = gen_model  # type: ignore[attr-defined]
            result = await self.bot.image_gen.generate(final_prompt, size=size)  # type: ignore[attr-defined]

        if "error" in result:
            await interaction.followup.send(f"Image generation failed: {result['error']}")
            return

        image_url_result = result.get("url", "")
        if not image_url_result:
            await interaction.followup.send("No image was returned.")
            return

        action = {"generate": "Generated", "variation": "Variation", "edit": "Edited"}.get(mode, "Generated")
        embed = discord.Embed(
            title=f"Image {action}",
            description=f"**Prompt:** {result.get('revised_prompt', prompt)[:2000]}",
            color=discord.Color.purple(),
            url=image_url_result,
        )
        embed.set_image(url=image_url_result)
        embed.set_footer(text=f"Model: {result.get('model', gen_model)} | Mode: {mode}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="imagemodels", description="List available image generation models.")
    async def image_models(self, interaction: discord.Interaction) -> None:
        models = self.bot.image_gen.get_available_models()  # type: ignore[attr-defined]
        lines = "\n".join(f"• `{m}`" for m in models)
        embed = discord.Embed(
            title="Image Generation Models",
            description=f"Current default: `{self.bot.settings.image_gen_model}`\n\n{lines}",
            color=discord.Color.purple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="summarize", description="Summarize text with key points.")
    async def summarize(self, interaction: discord.Interaction, text: str) -> None:
        await self._run_ai(
            interaction,
            text,
            instruction="Summarize this text in bullet points and include action items.",
            temperature=0.2,
        )

    @app_commands.command(name="translate", description="Translate text to a target language.")
    async def translate(
        self, interaction: discord.Interaction, target_language: str, text: str
    ) -> None:
        await self._run_ai(
            interaction,
            text,
            instruction=f"Translate to {target_language}. Keep original meaning and tone.",
            temperature=0.1,
        )

    @app_commands.command(name="rewrite", description="Rewrite text in a specific style.")
    async def rewrite(
        self, interaction: discord.Interaction, style: str, text: str
    ) -> None:
        await self._run_ai(
            interaction,
            text,
            instruction=f"Rewrite this in {style} style with better clarity.",
            temperature=0.5,
        )

    CODER_MODEL = AGENT_PRESETS["coder-pro"]["model"]

    @app_commands.command(name="code", description="Generate or fix code snippets.")
    async def code(
        self, interaction: discord.Interaction, language: str, request: str
    ) -> None:
        await self._run_ai(
            interaction,
            request,
            instruction=(
                f"You are a senior {language} engineer. Provide production-ready, working code. "
                "Include type hints, error handling, and brief comments on key parts. "
                "If the request is unclear, state assumptions and provide the best solution."
            ),
            temperature=0.3,
            override_model=self.CODER_MODEL,
        )

    @app_commands.command(name="codereview", description="Get AI code review with suggestions.")
    async def codereview(self, interaction: discord.Interaction, code: str, language: str = "") -> None:
        lang_hint = f" ({language})" if language else ""
        await self._run_ai(
            interaction,
            code,
            instruction=(
                f"Review this code{lang_hint} like a principal engineer. "
                "Be thorough but constructive. Cover: "
                "1) Bugs & logic errors 2) Security vulnerabilities 3) Performance bottlenecks "
                "4) Code quality & maintainability 5) Specific, actionable improvements. "
                "Format with clear sections and code examples."
            ),
            temperature=0.3,
            override_model=self.CODER_MODEL,
        )

    @app_commands.command(name="debug", description="Get debugging help for your code and errors.")
    async def debug(
        self, interaction: discord.Interaction, code: str, error: str = "", description: str = ""
    ) -> None:
        context = f"Error: {error}\n\n" if error else ""
        context += f"Description: {description}\n\n" if description else ""
        context += f"Code:\n{code}"
        await self._run_ai(
            interaction,
            context,
            instruction=(
                "You are a senior debugging expert. Analyze the code and error systematically. "
                "1) Identify the root cause 2) Explain why it happens in simple terms "
                "3) Show the exact fix 4) Suggest how to prevent similar bugs. "
                "If the error is incomplete, ask clarifying questions."
            ),
            temperature=0.3,
            override_model=self.CODER_MODEL,
        )

    @app_commands.command(name="refactor", description="Refactor code with explanation.")
    async def refactor(self, interaction: discord.Interaction, code: str, target: str = "") -> None:
        target_hint = f" Focus on: {target}." if target else ""
        await self._run_ai(
            interaction,
            code,
            instruction=(
                f"Refactor this code to be cleaner, more maintainable, and more efficient.{target_hint} "
                "Show the improved code and explain each change: "
                "1) What was wrong 2) How the fix improves it 3) Best practices applied."
            ),
            temperature=0.3,
            override_model=self.CODER_MODEL,
        )

    @app_commands.command(name="explaincode", description="Explain what code does in simple terms.")
    async def explaincode(self, interaction: discord.Interaction, code: str, language: str = "") -> None:
        lang_hint = f" ({language})" if language else ""
        await self._run_ai(
            interaction,
            code,
            instruction=(
                f"Explain this code{lang_hint} in simple, plain language. "
                "Assume the reader is learning to code. Cover: "
                "1) Overall purpose 2) How it works step by step "
                "3) Key concepts used 4) Any potential issues or improvements. "
                "Use analogies where helpful."
            ),
            temperature=0.4,
            override_model=self.CODER_MODEL,
        )

    @app_commands.command(name="setpersona", description="Set your AI persona preference.")
    async def set_persona(self, interaction: discord.Interaction, persona: str) -> None:
        await self.bot.db.set_user_profile(interaction.user.id, "persona", persona[:500])  # type: ignore[attr-defined]
        await interaction.response.send_message("Persona updated.", ephemeral=True)

    @app_commands.command(name="agents", description="List available AI agent presets.")
    async def agents(self, interaction: discord.Interaction) -> None:
        lines = []
        for key, info in AGENT_PRESETS.items():
            lines.append(f"`{key}` -> {info['model']} ({info['desc']})")
        embed = discord.Embed(
            title="AI Agent Presets",
            description="\n".join(lines),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="agent", description="Choose your default AI agent preset.")
    async def agent(self, interaction: discord.Interaction, name: str) -> None:
        key = name.strip().lower()
        if key not in AGENT_PRESETS:
            await interaction.response.send_message(
                f"Unknown agent `{name}`. Use `/agents` to see options.",
                ephemeral=True,
            )
            return
        await self.bot.db.set_user_profile(interaction.user.id, "agent_model", key)  # type: ignore[attr-defined]
        info = AGENT_PRESETS[key]
        await interaction.response.send_message(
            f"Default agent set to `{key}` ({info['model']}).",
            ephemeral=True,
        )

    @app_commands.command(name="clearhistory", description="Clear AI conversation history for this channel.")
    async def clear_history(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id if interaction.guild else 0
        count = await self.bot.db.clear_channel_history(guild_id, interaction.channel_id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            f"Cleared {count} history messages for this channel.", ephemeral=True
        )

    @app_commands.command(name="mypreferences", description="Show learned preferences about you.")
    async def my_preferences(self, interaction: discord.Interaction) -> None:
        prefs = await self.bot.db.get_user_preferences(interaction.user.id)  # type: ignore[attr-defined]
        lines: list[str] = []
        if prefs.get("preferred_language"):
            lines.append(f"**Language:** {prefs['preferred_language']}")
        if prefs.get("preferred_tone"):
            lines.append(f"**Tone:** {prefs['preferred_tone']}")
        if prefs.get("communication_style"):
            lines.append(f"**Style:** {prefs['communication_style']}")
        if prefs.get("topics"):
            topics = prefs["topics"]
            if isinstance(topics, list) and topics:
                lines.append(f"**Topics:** {', '.join(str(t) for t in topics)}")
        if not lines:
            await interaction.response.send_message(
                "I haven't learned your preferences yet. Chat with me more!", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="Your Learned Preferences",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="mymemory", description="Show what the bot remembers about you.")
    async def my_memory(self, interaction: discord.Interaction) -> None:
        facts = await self.bot.db.get_user_memory(interaction.user.id)  # type: ignore[attr-defined]
        if not facts:
            await interaction.response.send_message(
                "I don't have any stored facts about you yet.", ephemeral=True
            )
            return
        lines = [f"**{k}**: {v}" for k, v in facts.items()]
        embed = discord.Embed(
            title="Your Stored Memory",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearmemory", description="Clear all stored facts about you.")
    async def clear_memory(self, interaction: discord.Interaction) -> None:
        await self.bot.memory.clear_user_memory(interaction.user.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            "All stored facts about you have been cleared.", ephemeral=True
        )

    @app_commands.command(name="usage", description="Show token usage per provider.")
    async def usage(self, interaction: discord.Interaction) -> None:
        summary = self.bot.llm.get_usage_summary()  # type: ignore[attr-defined]
        await interaction.response.send_message(f"```{summary}```", ephemeral=True)

    # ---- Knowledge Base ----

    @app_commands.command(name="train", description="Teach the bot new knowledge.")
    async def train(self, interaction: discord.Interaction, topic: str, content: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        await self.bot.db.add_knowledge(interaction.guild.id, interaction.user.id, topic, content)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            f"✅ Trained on `{topic}`. I'll use this in future responses.", ephemeral=True
        )

    @app_commands.command(name="knowledge", description="List or remove trained knowledge.")
    async def knowledge(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        items = await self.bot.db.list_knowledge(interaction.guild.id)  # type: ignore[attr-defined]
        if not items:
            await interaction.response.send_message("No trained knowledge yet.", ephemeral=True)
            return
        lines = [f"`#{i['id']}` **{i['topic']}**: {i['content'][:80]}" for i in items[:20]]
        await interaction.response.send_message("🧠 **Knowledge Base**\n" + "\n".join(lines), ephemeral=True)

    # --- Conversation Threads ---

    @app_commands.command(name="thread", description="Create or switch to a conversation thread.")
    async def thread_cmd(self, interaction: discord.Interaction, title: str) -> None:
        tid = await self.bot.db.create_thread(  # type: ignore[attr-defined]
            interaction.user.id, interaction.guild_id or 0, interaction.channel_id, title
        )
        await interaction.response.send_message(f"🧵 New thread `{title}` (ID: {tid}).", ephemeral=True)

    @app_commands.command(name="forget", description="Clear AI memory about a topic.")
    async def forget(self, interaction: discord.Interaction, topic: str) -> None:
        await self.bot.db.set_user_memory(interaction.user.id, f"forget_{topic}", "")  # type: ignore[attr-defined]
        await interaction.response.send_message(f"I'll try to forget about `{topic}`.", ephemeral=True)

    @app_commands.command(name="context", description="Show what I know about our conversation.")
    async def show_context(self, interaction: discord.Interaction) -> None:
        facts = await self.bot.db.get_user_memory(interaction.user.id)  # type: ignore[attr-defined]
        prefs = await self.bot.db.get_user_preferences(interaction.user.id)  # type: ignore[attr-defined]
        parts = []
        if facts:
            parts.append("**Facts:**\n" + "\n".join(f"- {k}: {v}" for k, v in facts.items()))
        if prefs.get("preferred_language"):
            parts.append(f"**Language:** {prefs['preferred_language']}")
        if prefs.get("preferred_tone"):
            parts.append(f"**Tone:** {prefs['preferred_tone']}")
        if not parts:
            await interaction.response.send_message("I don't have much context about you yet.", ephemeral=True)
            return
        await interaction.response.send_message("📋 **My Context About You**\n" + "\n\n".join(parts), ephemeral=True)

    @app_commands.command(name="custom", description="Set a custom instruction for the AI.")
    async def custom_instruction(self, interaction: discord.Interaction, instruction: str) -> None:
        await self.bot.db.set_user_profile(interaction.user.id, "persona", instruction)  # type: ignore[attr-defined]
        await interaction.response.send_message("Custom instruction saved! I'll follow this.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AICog(bot))
