#!/usr/bin/env python3
"""
KrishiNet-BRICS Local Messaging Chat Simulator CLI.
Enables instant interactive testing and 1-command scripted replay of farmer conversations
without requiring a live Twilio or Meta account (zero-network DEMO_MODE).

Usage:
    python scripts/sim_chat.py --interactive
    python scripts/sim_chat.py --replay maharashtra_cotton
    python scripts/sim_chat.py --replay brazil_soybean
    python scripts/sim_chat.py --replay free_state_maize
"""

import argparse
import asyncio
import os
import sys
from typing import Dict, List, Optional

# Ensure services/api/src is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "api", "src")))

from app.messaging.crypto import normalize_phone_number
from app.messaging.engine.fsm import ConversationEngine
from app.messaging.providers.base import InboundMessageDTO
from app.messaging.providers.router import get_simulator_provider
from app.messaging.segment_calc import calculate_segments
from app.db.session import AsyncSessionLocal, async_engine
from app.db.base import Base


COLOR_RESET = "\033[0m"
COLOR_GREEN = "\033[32m"
COLOR_BLUE = "\033[34m"
COLOR_YELLOW = "\033[33m"
COLOR_CYAN = "\033[36m"
COLOR_BOLD = "\033[1m"
COLOR_GRAY = "\033[90m"


def print_banner(channel: str, phone: str, title: str = "Local Simulator"):
    print("\n" + "=" * 65)
    print(f"{COLOR_BOLD}{COLOR_GREEN}🌾 KrishiNet-BRICS Chat Simulator [{channel.upper()}]{COLOR_RESET}")
    print(f"Target Farmer: {phone} | Scenario: {COLOR_CYAN}{title}{COLOR_RESET}")
    print("=" * 65)


def print_farmer_bubble(text: str, msg_type: str = "text"):
    print(f"\n{COLOR_BOLD}{COLOR_BLUE}🧑‍🌾 Farmer [{msg_type}]:{COLOR_RESET}")
    print(f"  ┌{'─' * 55}")
    for line in text.split("\n"):
        print(f"  │ {line}")
    print(f"  └{'─' * 55}")


def print_bot_bubble(text: str, channel: str = "whatsapp"):
    seg_info = calculate_segments(text)
    cost = 0.0075 * int(seg_info["segments"]) if channel == "sms" else 0.005

    print(f"\n{COLOR_BOLD}{COLOR_GREEN}🤖 KrishiNet Bot [{channel.upper()}]:{COLOR_RESET}")
    print(f"  ┌{'─' * 55}")
    for line in text.split("\n"):
        print(f"  │ {line}")
    print(f"  ├{'─' * 55}")
    print(
        f"  │ {COLOR_GRAY}Encoding: {seg_info['encoding']} | Segments: {seg_info['segments']} "
        f"({seg_info['encoded_length']} units) | Est. Cost: ${cost:.4f}{COLOR_RESET}"
    )
    print(f"  └{'─' * 55}")


async def dispatch_step(
    engine: ConversationEngine,
    phone: str,
    channel: str,
    text: Optional[str] = None,
    msg_type: str = "text",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    media_url: Optional[str] = None
) -> str:
    sim_provider = get_simulator_provider()
    media_bytes = None
    if msg_type in ["image", "voice"]:
        media_bytes = await sim_provider.download_media(media_url or "synthetic_media.jpg")

    inbound = InboundMessageDTO(
        provider="simulator",
        provider_message_id=f"sim-cli-{os.urandom(4).hex()}",
        from_phone=phone,
        to_phone="+911140001234",
        channel=channel,
        message_type=msg_type,
        body=text,
        media_url=media_url,
        latitude=lat,
        longitude=lon,
    )

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        reply = await engine.process_message(db, inbound, media_bytes)
        return reply


# --- Pre-scripted Demo Conversations ---

async def reset_session_for_phone(phone: str):
    from sqlalchemy import delete
    from app.models.messaging import MessageSession
    from app.messaging.crypto import hash_phone_number
    p_hash = hash_phone_number(phone)
    async with AsyncSessionLocal() as db:
        await db.execute(delete(MessageSession).where(MessageSession.phone_hash == p_hash))
        await db.commit()


async def replay_maharashtra_cotton():
    """
    Scenario 1: Hindi SMS conversation for Maharashtra cotton farmer (Nagpur).
    Demonstrates Devanagari script, GSM-7 vs UCS-2 segment accounting, consent receipt, and bollworm advisory.
    """
    phone = "+919820011223"
    await reset_session_for_phone(phone)
    channel = "sms"
    print_banner(channel, phone, "Maharashtra Cotton Farm (Hindi SMS)")

    engine = ConversationEngine()

    steps = [
        ("नमस्ते, मुझे कपास की फसल के लिए सलाह चाहिए", "text", None, None),
        ("2", "text", None, None),  # Choose Hindi
        ("1", "text", None, None),  # Accept Consent
        ("नागपुर, महाराष्ट्र", "text", None, None),  # Location text
        ("1", "text", None, None),  # Confirm location
        ("1", "text", None, None),  # Choose Cotton
        ("1", "text", None, None),  # Request Today's Advisory
    ]

    for user_input, msg_type, lat, lon in steps:
        print_farmer_bubble(user_input, msg_type)
        reply = await dispatch_step(engine, phone, channel, text=user_input, msg_type=msg_type, lat=lat, lon=lon)
        print_bot_bubble(reply, channel)
        await asyncio.sleep(0.4)

    print(f"\n{COLOR_GREEN}✅ Scenario 1 (Maharashtra Cotton SMS) completed successfully.{COLOR_RESET}\n")


async def replay_brazil_soybean():
    """
    Scenario 2: Portuguese WhatsApp conversation with leaf photo upload for soybean rust check.
    Demonstrates WhatsApp rich UI, EXIF stripping, Leaf Doctor disease ensemble, and organic recommendation.
    """
    phone = "+5545999887766"
    await reset_session_for_phone(phone)
    channel = "whatsapp"
    print_banner(channel, phone, "Paraná Soybean Farm (Portuguese WhatsApp + Leaf Doctor)")

    engine = ConversationEngine()

    steps = [
        ("Olá KrishiNet, preciso de ajuda na lavoura de soja", "text", None, None, None),
        ("4", "text", None, None, None),  # Choose Portuguese
        ("1", "text", None, None, None),  # Consent
        ("Cascavel, Paraná", "text", None, None, None),  # Location
        ("1", "text", None, None, None),  # Confirm location
        ("1", "text", None, None, None),  # Choose Soja (Soybean)
        ("2", "text", None, None, None),  # Choose Leaf Doctor
        ("Envio foto da folha com pontuações castanhas", "image", None, None, "https://cdn.krishinet.org/demo/soybean_rust_leaf.jpg"),
    ]

    for item in steps:
        user_input, msg_type, lat, lon, media = item
        print_farmer_bubble(user_input, msg_type)
        reply = await dispatch_step(engine, phone, channel, text=user_input, msg_type=msg_type, lat=lat, lon=lon, media_url=media)
        print_bot_bubble(reply, channel)
        await asyncio.sleep(0.4)

    print(f"\n{COLOR_GREEN}✅ Scenario 2 (Brazil Soybean WhatsApp) completed successfully.{COLOR_RESET}\n")


async def replay_free_state_maize():
    """
    Scenario 3: English WhatsApp conversation for Free State maize farm.
    Demonstrates GPS pin location, 3-day weather forecast, spray window calculation, and officer escalation.
    """
    phone = "+27821234567"
    await reset_session_for_phone(phone)
    channel = "whatsapp"
    print_banner(channel, phone, "Free State Maize Farm (English WhatsApp)")

    engine = ConversationEngine()

    steps = [
        ("Hi KrishiNet, starting new maize planting cycle", "text", None, None, None),
        ("1", "text", None, None, None),  # English
        ("1", "text", None, None, None),  # Consent
        ("Sending farm GPS pin", "location", -27.38, 26.62, None),  # Bothaville GPS
        ("3", "text", None, None, None),  # Choose Maize
        ("3", "text", None, None, None),  # 3-Day Weather & Spray Window
        ("5", "text", None, None, None),  # Officer Assistance
    ]

    for item in steps:
        user_input, msg_type, lat, lon, media = item
        print_farmer_bubble(user_input, msg_type)
        reply = await dispatch_step(engine, phone, channel, text=user_input, msg_type=msg_type, lat=lat, lon=lon, media_url=media)
        print_bot_bubble(reply, channel)
        await asyncio.sleep(0.4)

    print(f"\n{COLOR_GREEN}✅ Scenario 3 (Free State Maize WhatsApp) completed successfully.{COLOR_RESET}\n")


async def interactive_mode():
    """Live interactive terminal chat loop."""
    print("\n" + "=" * 65)
    print(f"{COLOR_BOLD}{COLOR_GREEN}🌾 KrishiNet Interactive Terminal Simulator{COLOR_RESET}")
    print("Commands: ':sms' to toggle SMS, ':wa' to toggle WhatsApp, ':photo' to simulate leaf upload, ':exit' to quit")
    print("=" * 65)

    phone = "+919876543210"
    channel = "whatsapp"
    engine = ConversationEngine()

    # Initial trigger
    reply = await dispatch_step(engine, phone, channel, text="hello")
    print_bot_bubble(reply, channel)

    while True:
        try:
            line = input(f"\n{COLOR_BLUE}You ({channel}) > {COLOR_RESET}").strip()
            if not line:
                continue
            if line.lower() in [":exit", "exit", "quit"]:
                break
            if line.lower() == ":sms":
                channel = "sms"
                print(f"{COLOR_YELLOW}[Switched to SMS channel]{COLOR_RESET}")
                continue
            if line.lower() == ":wa":
                channel = "whatsapp"
                print(f"{COLOR_YELLOW}[Switched to WhatsApp channel]{COLOR_RESET}")
                continue
            if line.lower() == ":photo":
                print_farmer_bubble("Uploaded leaf photo", "image")
                reply = await dispatch_step(engine, phone, channel, text="leaf photo", msg_type="image", media_url="mock_leaf.jpg")
                print_bot_bubble(reply, channel)
                continue

            reply = await dispatch_step(engine, phone, channel, text=line)
            print_bot_bubble(reply, channel)
        except (KeyboardInterrupt, EOFError):
            break

    print("\nGoodbye!\n")


def main():
    parser = argparse.ArgumentParser(description="KrishiNet-BRICS Chat Simulator CLI")
    parser.add_argument(
        "--replay",
        choices=["maharashtra_cotton", "brazil_soybean", "free_state_maize", "all"],
        help="Run an automated scripted demo conversation"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive conversational prompt in terminal"
    )
    args = parser.parse_args()

    if args.replay == "maharashtra_cotton":
        asyncio.run(replay_maharashtra_cotton())
    elif args.replay == "brazil_soybean":
        asyncio.run(replay_brazil_soybean())
    elif args.replay == "free_state_maize":
        asyncio.run(replay_free_state_maize())
    elif args.replay == "all":
        asyncio.run(replay_maharashtra_cotton())
        asyncio.run(replay_brazil_soybean())
        asyncio.run(replay_free_state_maize())
    else:
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
