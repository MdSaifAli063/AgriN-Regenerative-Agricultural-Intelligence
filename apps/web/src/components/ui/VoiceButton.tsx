"use client";

import React, { useState } from "react";
import { Volume2, VolumeX, Mic, MicOff, Loader2 } from "lucide-react";
import { Button } from "./Button";
import { cn } from "@/lib/utils";

export interface VoiceButtonProps {
  mode?: "speak" | "listen";
  textToSpeak?: string;
  onSpeechResult?: (transcript: string) => void;
  lang?: string;
  label?: string;
  size?: "sm" | "md" | "lg" | "icon";
  className?: string;
}

export function VoiceButton({
  mode = "speak",
  textToSpeak = "",
  onSpeechResult,
  lang = "en",
  label,
  size = "md",
  className,
}: VoiceButtonProps) {
  const [isActive, setIsActive] = useState(false);
  const [isSupported, setIsSupported] = useState(true);

  // 1. Text-to-Speech (Speak) Handler
  const handleSpeak = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      alert("Text-to-speech is not supported in this browser.");
      setIsSupported(false);
      return;
    }

    if (isActive) {
      window.speechSynthesis.cancel();
      setIsActive(false);
      return;
    }

    window.speechSynthesis.cancel(); // Stop any pending speech
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = lang;
    utterance.rate = 0.95; // Slightly slower for clear agronomic comprehension

    utterance.onstart = () => setIsActive(true);
    utterance.onend = () => setIsActive(false);
    utterance.onerror = () => setIsActive(false);

    window.speechSynthesis.speak(utterance);
  };

  // 2. Speech-to-Text (Listen) Handler
  const handleListen = () => {
    if (typeof window === "undefined") return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser. Please type your query.");
      setIsSupported(false);
      return;
    }

    if (isActive) {
      setIsActive(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = lang;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => setIsActive(true);
      recognition.onend = () => setIsActive(false);
      recognition.onerror = () => setIsActive(false);

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (onSpeechResult) {
          onSpeechResult(transcript);
        }
        setIsActive(false);
      };

      recognition.start();
    } catch {
      setIsActive(false);
    }
  };

  const handleClick = mode === "speak" ? handleSpeak : handleListen;

  const defaultAriaLabel =
    mode === "speak"
      ? isActive
        ? "Stop reading aloud"
        : "Read advice aloud"
      : isActive
      ? "Stop voice input"
      : "Start voice input";

  return (
    <Button
      type="button"
      onClick={handleClick}
      aria-label={label || defaultAriaLabel}
      variant={isActive ? "primary" : "secondary"}
      size={size}
      className={cn(
        "relative transition-all",
        isActive && "ring-2 ring-primary ring-offset-2 animate-pulse",
        className
      )}
    >
      {mode === "speak" ? (
        isActive ? (
          <VolumeX className="h-5 w-5 text-white" />
        ) : (
          <Volume2 className="h-5 w-5 text-primary" />
        )
      ) : isActive ? (
        <MicOff className="h-5 w-5 text-white" />
      ) : (
        <Mic className="h-5 w-5 text-primary" />
      )}
      {label && <span className="ml-2 font-medium">{label}</span>}
    </Button>
  );
}
