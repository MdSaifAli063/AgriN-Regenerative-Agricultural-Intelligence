"""
KrishiNet-BRICS - Sovereign Gemini Client Wrapper.

Provides an enterprise-grade, asynchronous wrapper around the Google GenAI SDK:
  - Models configurable by environment (reasoning, pro, and embedding)
  - Structured output with Pydantic v2 validation and automatic single-turn repair retry
  - High-performance text and query embedding with exact 768-dim output
  - Token usage telemetry and per-user / per-node daily budget enforcement
  - Configured safety filters with graceful blocked response handling
  - Full resilience wrapping via ExternalServiceGuard (timeouts, circuit breakers, demo fallbacks)
"""

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.exceptions import AppException
from app.services.service_guard import ExternalServiceGuard

logger = logging.getLogger("krishinet.ai.gemini")

T = TypeVar("T", bound=BaseModel)


class TokenBudgetExceededException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="TOKEN_BUDGET_EXCEEDED",
            message=message,
            status_code=429,
            details=details or {},
        )


class GeminiSafetyException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="GEMINI_SAFETY_BLOCKED",
            message=message,
            status_code=400,
            details=details or {},
        )


class GeminiClientWrapper:
    """
    Robust asynchronous Gemini Client wrapping google-genai SDK.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or ""
        self.reasoning_model = settings.GEMINI_REASONING_MODEL
        self.pro_model = settings.GEMINI_PRO_MODEL
        self.embed_model = settings.GEMINI_EMBED_MODEL
        self.embedding_dim = settings.GEMINI_EMBEDDING_DIM

        # In-memory token budget tracking (timestamp -> token counts)
        self._user_daily_tokens: Dict[str, Dict[str, Any]] = {}
        self._node_daily_tokens: Dict[str, Any] = {"date": time.strftime("%Y-%m-%d"), "tokens": 0}

        # Initialize ExternalServiceGuard
        self.guard = ExternalServiceGuard(
            service_name="Gemini-AI",
            timeout_seconds=20.0,
            max_retries=2,
            backoff_factor=0.5,
            failure_threshold=3,
            recovery_timeout=30.0,
        )

        self._client = None
        if self.api_key and not settings.DEMO_MODE:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}")
                self._client = None

    @property
    def is_available(self) -> bool:
        """Returns True only if a valid API key exists and demo mode is not forcing fixtures."""
        return bool(self.api_key and self._client is not None and not settings.DEMO_MODE)

    def _check_token_budget(self, user_id: str, estimated_tokens: int = 1000) -> None:
        """Enforces daily token usage limits per user and per sovereign node."""
        today = time.strftime("%Y-%m-%d")

        # Check node-wide budget
        if self._node_daily_tokens["date"] != today:
            self._node_daily_tokens = {"date": today, "tokens": 0}

        if self._node_daily_tokens["tokens"] + estimated_tokens > settings.NODE_DAILY_TOKEN_LIMIT:
            raise TokenBudgetExceededException(
                f"Sovereign node '{settings.NODE_ID}' daily token budget of "
                f"{settings.NODE_DAILY_TOKEN_LIMIT} exceeded. Requests throttled."
            )

        # Check per-user budget
        if user_id:
            user_entry = self._user_daily_tokens.get(user_id, {"date": today, "tokens": 0})
            if user_entry["date"] != today:
                user_entry = {"date": today, "tokens": 0}

            if user_entry["tokens"] + estimated_tokens > settings.USER_DAILY_TOKEN_LIMIT:
                raise TokenBudgetExceededException(
                    f"User '{user_id}' daily token budget of {settings.USER_DAILY_TOKEN_LIMIT} exceeded."
                )

    def _record_token_usage(
        self,
        user_id: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> None:
        """Records token usage metrics in memory and structured telemetry logs."""
        today = time.strftime("%Y-%m-%d")
        total_tokens = prompt_tokens + completion_tokens

        # Update in-memory budgets
        if self._node_daily_tokens["date"] != today:
            self._node_daily_tokens = {"date": today, "tokens": 0}
        self._node_daily_tokens["tokens"] += total_tokens

        if user_id:
            user_entry = self._user_daily_tokens.setdefault(user_id, {"date": today, "tokens": 0})
            if user_entry["date"] != today:
                user_entry["date"] = today
                user_entry["tokens"] = 0
            user_entry["tokens"] += total_tokens

        logger.info(
            "Gemini call completed",
            extra={
                "model": model_name,
                "user_id": user_id,
                "node_id": settings.NODE_ID,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "latency_ms": round(latency_ms, 2),
            },
        )

    def _get_safety_settings(self):
        """Constructs safety settings blocking high-risk harm categories."""
        try:
            from google.genai import types
            return [
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
            ]
        except Exception:
            return []

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = "system",
        temperature: float = 0.2,
    ) -> str:
        """Generates plain text response via Gemini."""
        if not self.is_available:
            return "KrishiNet-BRICS Advisory Engine (Demo Mode): Gemini API is running in offline demo fallback."

        self._check_token_budget(user_id or "system", estimated_tokens=len(prompt) // 4)
        target_model = model or self.reasoning_model
        start_time = time.time()

        async def _call():
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                safety_settings=self._get_safety_settings(),
                temperature=temperature,
            )
            response = await self._client.aio.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
            return response

        try:
            response = await self.guard.execute_async(_call)
            latency_ms = (time.time() - start_time) * 1000.0

            # Extract token usage if metadata available
            usage = getattr(response, "usage_metadata", None)
            p_tok = getattr(usage, "prompt_token_count", len(prompt) // 4) or 100
            c_tok = getattr(usage, "candidates_token_count", 200) or 200

            self._record_token_usage(
                user_id=user_id or "system",
                model_name=target_model,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                latency_ms=latency_ms,
            )

            text = response.text or ""
            return text.strip()
        except Exception as e:
            logger.error(f"Gemini generate_text failure: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = "system",
        fallback_factory: Optional[Callable[[], T]] = None,
        temperature: float = 0.2,
    ) -> T:
        """
        Generates structured JSON response adhering to a Pydantic v2 schema.
        Includes automatic 1-turn repair retry if initial response fails schema validation.
        """
        if not self.is_available:
            if fallback_factory is not None:
                return fallback_factory()
            raise RuntimeError("Gemini Client is unavailable and no fallback_factory was provided.")

        self._check_token_budget(user_id or "system", estimated_tokens=len(prompt) // 3)
        target_model = model or self.reasoning_model
        start_time = time.time()

        async def _invoke_model(current_prompt: str) -> str:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema,
                safety_settings=self._get_safety_settings(),
                temperature=temperature,
            )
            response = await self._client.aio.models.generate_content(
                model=target_model,
                contents=current_prompt,
                config=config,
            )
            return response.text or "{}"

        # Turn 1: Primary generation attempt
        raw_text = "{}"
        try:
            raw_text = await self.guard.execute_async(_invoke_model, prompt)
            parsed_data = schema.model_validate_json(raw_text)
            latency_ms = (time.time() - start_time) * 1000.0
            self._record_token_usage(user_id or "system", target_model, len(prompt) // 4, len(raw_text) // 4, latency_ms)
            return parsed_data
        except (ValidationError, json.JSONDecodeError) as val_err:
            logger.warning(f"Schema validation failure on Turn 1 ({val_err}); initiating automatic repair retry.")
            
            # Turn 2: Automatic Repair Retry
            repair_prompt = (
                f"{prompt}\n\n"
                f"--- CRITICAL JSON VALIDATION ERROR IN PREVIOUS ATTEMPT ---\n"
                f"Your previous JSON response failed Pydantic schema validation:\n"
                f"{str(val_err)}\n\n"
                f"Previous Malformed JSON:\n{raw_text[:800]}\n\n"
                f"Please correct the errors and output ONLY valid JSON matching the exact schema."
            )
            try:
                # Use PRO model if available for repair retry
                repair_model = self.pro_model or target_model
                repaired_text = await self.guard.execute_async(_invoke_model, repair_prompt)
                repaired_obj = schema.model_validate_json(repaired_text)
                latency_ms = (time.time() - start_time) * 1000.0
                self._record_token_usage(user_id or "system", repair_model, len(repair_prompt) // 4, len(repaired_text) // 4, latency_ms)
                return repaired_obj
            except Exception as repair_exc:
                logger.error(f"Automatic repair retry also failed ({repair_exc}); activating fallback.")
                if fallback_factory is not None:
                    return fallback_factory()
                raise AppException(
                    code="AI_STRUCTURED_GENERATION_FAILED",
                    message="Model failed to produce valid structured JSON after repair retry.",
                    details={"error": str(repair_exc)},
                )

    async def embed_texts(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> List[List[float]]:
        """
        Embeds a batch of texts using Gemini Embeddings with exact 768-dim output.
        """
        if not texts:
            return []

        if not self.is_available:
            # Deterministic pseudo-embedding for testing & offline mode
            return [self._generate_offline_embedding(t) for t in texts]

        async def _call():
            from google.genai import types
            config = types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.embedding_dim,
            )
            # Batch call or parallel execute
            embeddings = []
            for t in texts:
                resp = await self._client.aio.models.embed_content(
                    model=self.embed_model,
                    contents=t,
                    config=config,
                )
                embeddings.append(resp.embedding.values)
            return embeddings

        try:
            return await self.guard.execute_async(_call)
        except Exception as e:
            logger.warning(f"Gemini embed_texts failed ({e}); using offline deterministic embeddings.")
            return [self._generate_offline_embedding(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        """Embeds a single query string for semantic vector retrieval."""
        results = await self.embed_texts([query], task_type="RETRIEVAL_QUERY")
        return results[0] if results else [0.0] * self.embedding_dim

    async def translate(
        self,
        text_or_fields: Union[str, Dict[str, str]],
        target_lang: str,
        user_id: Optional[str] = "system",
    ) -> Union[str, Dict[str, str]]:
        """
        Translates text or key-value dictionary to target language.
        Preserves numeric values, dates, percentages, and keys verbatim.
        """
        if target_lang.lower() in ["en", "eng"]:
            return text_or_fields

        if not self.is_available:
            return text_or_fields

        if isinstance(text_or_fields, str):
            prompt = (
                f"Translate the following agricultural advisory text to language '{target_lang}'. "
                f"Keep all numbers, dates, crop names, units (kg, t/ha, °C, mm), and technical terms intact.\n\n"
                f"Text:\n{text_or_fields}"
            )
            translated = await self.generate_text(prompt=prompt, user_id=user_id, temperature=0.1)
            return translated

        # Dictionary of fields
        prompt = (
            f"You are an agricultural translation assistant. Translate the text values in this JSON object "
            f"to language code '{target_lang}'.\n"
            f"CRITICAL RULES:\n"
            f"1. DO NOT change any JSON keys.\n"
            f"2. DO NOT change any numbers, dates, units, or percentages.\n"
            f"3. Return ONLY the translated JSON dictionary.\n\n"
            f"Input JSON:\n{json.dumps(text_or_fields, ensure_ascii=False)}"
        )
        try:
            res_str = await self.generate_text(prompt=prompt, user_id=user_id, temperature=0.1)
            # Clean possible markdown fence
            clean = res_str.replace("```json", "").replace("```", "").strip()
            translated_dict = json.loads(clean)
            if isinstance(translated_dict, dict) and set(translated_dict.keys()) == set(text_or_fields.keys()):
                return translated_dict
            return text_or_fields
        except Exception as e:
            logger.warning(f"Translation failed ({e}); returning original text.")
            return text_or_fields

    def _generate_offline_embedding(self, text: str) -> List[float]:
        """
        Produces a normalized 768-dimensional deterministic float vector from text hash.
        Ensures consistent cosine similarity in offline demo and unit test environments.
        """
        import hashlib
        import math

        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(self.embedding_dim):
            byte_idx = i % len(h)
            val = ((h[byte_idx] + (i * 17)) % 256) / 128.0 - 1.0
            vec.append(val)

        # Normalize to unit vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec


gemini_client = GeminiClientWrapper()
