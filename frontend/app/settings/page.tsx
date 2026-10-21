"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Sun,
  Moon,
  Laptop,
  User,
  Sliders,
  Mic,
  Shield,
  Download,
  Trash2,
  Check,
  Sparkles,
  Key,
  Volume2,
  HelpCircle,
  Save,
  RotateCcw,
  Award,
  ArrowRight,
  Eye,
  EyeOff,
  Bell,
  Cpu,
} from "lucide-react";
import { CurioNav } from "@/components/curio/CurioNav";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { useSettingsStore } from "@/stores/settingsStore";
import { useAuthStore } from "@/stores/authStore";
import { AppTheme, CharacterAvatarId, FeynmanRigorLevel } from "@/types/settings";
import { curioToast } from "@/components/curio/CurioToast";

type SettingsTab = "appearance" | "profile" | "learning" | "audio" | "privacy" | "api";

function SettingsContent() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as SettingsTab) || "appearance";
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);

  const { user } = useAuthStore();
  const {
    theme,
    profile,
    learning,
    audio,
    privacy,
    stats,
    setTheme,
    updateProfile,
    updateLearning,
    updateAudio,
    updatePrivacy,
    resetToDefaults,
    exportDataAsJson,
    initSettings,
  } = useSettingsStore();

  // Local form states
  const [profileForm, setProfileForm] = useState(profile);
  const [learningForm, setLearningForm] = useState(learning);
  const [audioForm, setAudioForm] = useState(audio);
  const [privacyForm, setPrivacyForm] = useState(privacy);
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [isPlayingTestVoice, setIsPlayingTestVoice] = useState(false);
  const [savedFeedback, setSavedFeedback] = useState(false);

  useEffect(() => {
    initSettings();
  }, [initSettings]);

  useEffect(() => {
    const tabParam = searchParams.get("tab") as SettingsTab;
    if (tabParam) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  useEffect(() => {
    setProfileForm({
      ...profile,
      displayName: profile.displayName || user?.name || (user?.email ? user.email.split("@")[0] : ""),
      email: user?.email || profile.email || "",
    });
    setLearningForm(learning);
    setAudioForm(audio);
    setPrivacyForm(privacy);
  }, [profile, learning, audio, privacy, user]);

  const handleSaveAll = () => {
    updateProfile(profileForm);
    updateLearning(learningForm);
    updateAudio(audioForm);
    updatePrivacy(privacyForm);
    setSavedFeedback(true);
    curioToast.success("Preferences Saved", "All laboratory configurations have been updated.");
    setTimeout(() => setSavedFeedback(false), 2500);
  };

  const handleExportData = () => {
    const jsonStr = exportDataAsJson();
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `curio_laboratory_export_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    curioToast.success("Export Complete", "Laboratory configuration saved as JSON file.");
  };

  const handlePlayVoiceSample = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      curioToast.info("Voice Simulation", "Speech synthesis sample simulated.");
      return;
    }
    setIsPlayingTestVoice(true);
    window.speechSynthesis.cancel();
    const sampleText = `Hello! I'm ${audioForm.voicePersona.split(" ")[1] || "Curio"}. Explain your concept to me like I am twelve years old.`;
    const utterance = new SpeechSynthesisUtterance(sampleText);
    utterance.rate = audioForm.speechRate;
    utterance.pitch = audioForm.pitch;
    utterance.onend = () => setIsPlayingTestVoice(false);
    utterance.onerror = () => setIsPlayingTestVoice(false);
    window.speechSynthesis.speak(utterance);
  };

  const tabs = [
    { id: "appearance" as const, label: "APPEARANCE & THEME", icon: Sun },
    { id: "profile" as const, label: "PROFILE & IDENTITY", icon: User },
    { id: "learning" as const, label: "FEYNMAN LABORATORY", icon: Sliders },
    { id: "audio" as const, label: "VOICE & AUDIO", icon: Mic },
    { id: "privacy" as const, label: "DATA & PRIVACY", icon: Shield },
    { id: "api" as const, label: "API KEYS & MODELS", icon: Cpu },
  ];

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Global Navigation */}
      <CurioNav activeRoute="settings" />

      {/* Sub-bar with Breadcrumb & Save Action */}
      <div className="w-full bg-white/80 dark:bg-[#080F1A]/90 border-b border-fog dark:border-[#1E3652] px-4 md:px-8 py-2.5 sticky top-0 z-20 backdrop-blur-xs">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-mono">
            <Link href="/dashboard" className="text-navy/60 dark:text-[#F0F4F8]/60 hover:text-navy dark:hover:text-white transition-colors">
              DASHBOARD
            </Link>
            <span className="text-fog dark:text-[#1E3652]">/</span>
            <span className="font-bold text-navy dark:text-[#F0F4F8]">SETTINGS & PREFERENCES</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSaveAll}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] font-mono text-xs font-bold uppercase transition-all shadow-[2px_2px_0_0_#0F2B4A] dark:shadow-[2px_2px_0_0_#040910] active:translate-y-[1px] cursor-pointer ${
                savedFeedback
                  ? "bg-emerald-600 text-white border-2 border-emerald-700"
                  : "bg-gap-orange text-white border-2 border-gap-orange hover:bg-[#e05809]"
              }`}
            >
              {savedFeedback ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>SAVED!</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>SAVE PREFERENCES</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main Settings Body */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 md:px-8 py-8 md:py-10">
        {/* Page Title & Mission */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2 font-mono text-xs uppercase tracking-wider text-cobalt font-bold">
            <span className="w-2 h-2 rounded-full bg-cobalt animate-pulse" />
            CURIO SYSTEM CONTROL
          </div>
          <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-navy dark:text-[#F0F4F8] tracking-tight">
            Settings & Laboratory Preferences
          </h1>
          <p className="font-sans text-sm text-navy/70 dark:text-[#F0F4F8]/70 max-w-2xl mt-1">
            Customize your Feynman inquiry rigor, theme aesthetics, speech synthesis, and identity details.
          </p>
        </div>

        {/* 2-Column Responsive Layout: Tabs on left, Active panel on right */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Navigation Tabs */}
          <div className="lg:col-span-4 space-y-1 bg-white dark:bg-[#0B1524] border border-fog dark:border-[#1E3652] rounded-[6px] p-2.5 shadow-xs">
            <div className="px-3 py-2 font-mono text-[10px] uppercase tracking-wider font-bold text-navy/50 dark:text-[#F0F4F8]/50">
              CONFIG SECTIONS
            </div>
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-[4px] text-xs font-mono font-bold uppercase transition-all cursor-pointer ${
                    isActive
                      ? "bg-navy dark:bg-cobalt text-white shadow-[2px_2px_0_0_#0F2B4A] dark:shadow-[2px_2px_0_0_#040910]"
                      : "text-navy/75 dark:text-[#F0F4F8]/75 hover:text-navy dark:hover:text-white hover:bg-ice/70 dark:hover:bg-[#101F33]"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={`w-4 h-4 ${
                        isActive ? "text-gap-orange dark:text-white" : "text-navy/50 dark:text-[#F0F4F8]/50"
                      }`}
                    />
                    <span>{tab.label}</span>
                  </div>
                  {isActive && <ArrowRight className="w-3.5 h-3.5 text-gap-orange dark:text-white" />}
                </button>
              );
            })}

            {/* Quick Profile Snapshot Card in Sidebar */}
            <div className="mt-4 pt-4 border-t border-fog dark:border-[#1E3652] p-2 bg-ice/40 dark:bg-[#101F33] rounded-[4px]">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-8 h-8 rounded-[4px] bg-navy text-white flex items-center justify-center font-mono text-xs font-bold border border-navy shadow-[1px_1px_0_0_#0F2B4A] dark:shadow-[1px_1px_0_0_#040910]">
                  {profile.characterAvatar === "STUDENT"
                    ? "🎓"
                    : profile.characterAvatar === "TEACHER"
                    ? "📐"
                    : "⚡"}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-sans text-xs font-bold text-navy dark:text-[#F0F4F8] truncate">
                    {profileForm.displayName || "Learner"}
                  </div>
                  <div className="font-mono text-[10px] text-cobalt font-semibold">
                    LVL {profile.feynmanLevel} • {profile.levelTitle}
                  </div>
                </div>
              </div>
              <div className="flex justify-between items-center text-[10px] font-mono text-navy/60 dark:text-[#F0F4F8]/60 pt-2 border-t border-fog/50 dark:border-[#1E3652]">
                <span>GAPS RESOLVED:</span>
                <span className="font-bold text-gap-orange">{stats.gapsResolved}</span>
              </div>
            </div>
          </div>

          {/* Right Column: Tab Content */}
          <div className="lg:col-span-8 space-y-6">
            {/* TAB 1: APPEARANCE & THEME */}
            {activeTab === "appearance" && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                {/* Theme Selector */}
                <div className="bg-white dark:bg-[#0B1524] border border-fog dark:border-[#1E3652] rounded-[6px] p-6 shadow-sm">
                  <div className="flex items-center gap-2.5 mb-2">
                    <Sun className="w-5 h-5 text-gap-orange" />
                    <h3 className="font-heading text-base font-bold text-navy dark:text-[#F0F4F8]">
                      Interface Theme & Color System
                    </h3>
                  </div>
                  <p className="font-sans text-xs text-navy/70 dark:text-[#F0F4F8]/70 mb-5">
                    Curio supports both pure Light Editorial and Deep Obsidian Blueprint themes without disrupting readability or isometric keycap aesthetics.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {/* Light Option */}
                    <button
                      type="button"
                      onClick={() => setTheme("light")}
                      className={`flex flex-col items-start p-4 rounded-[6px] border-2 transition-all cursor-pointer text-left relative ${
                        theme === "light"
                          ? "border-navy dark:border-cobalt bg-ice dark:bg-[#101F33] shadow-[3px_3px_0_0_#0F2B4A] dark:shadow-[3px_3px_0_0_#040910]"
                          : "border-fog dark:border-[#1E3652] bg-white dark:bg-[#0E1A2B] hover:border-navy/50 dark:hover:border-cobalt/50"
                      }`}
                    >
                      <div className="flex items-center justify-between w-full mb-3">
                        <div className="flex items-center gap-2">
                          <Sun className="w-4 h-4 text-gap-orange" />
                          <span className="font-mono text-xs font-bold uppercase text-navy dark:text-[#F0F4F8]">
                            Light Mode
                          </span>
                        </div>
                        {theme === "light" && (
                          <span className="w-2 h-2 rounded-full bg-gap-orange" />
                        )}
                      </div>
                      <div className="w-full h-16 rounded bg-[#E8EEF3] border border-[#C4CDD6] p-2 flex flex-col justify-between">
                        <div className="w-1/2 h-2 bg-[#0F2B4A] rounded" />
                        <div className="flex gap-1">
                          <div className="w-1/3 h-3 bg-white rounded border border-[#C4CDD6]" />
                          <div className="w-1/4 h-3 bg-[#3A63FF] rounded" />
                        </div>
                      </div>
                      <span className="font-mono text-[10px] text-navy/60 dark:text-[#F0F4F8]/60 mt-2">
                        Curio Ice & Editorial Navy
                      </span>
                    </button>

                    {/* Dark Option */}
                    <button
                      type="button"
                      onClick={() => setTheme("dark")}
                      className={`flex flex-col items-start p-4 rounded-[6px] border-2 transition-all cursor-pointer text-left relative ${
                        theme === "dark"
                          ? "border-cobalt bg-navy dark:bg-[#101F33] shadow-[3px_3px_0_0_#3A63FF]"
                          : "border-fog dark:border-[#1E3652] bg-white dark:bg-[#0E1A2B] hover:border-navy/50 dark:hover:border-cobalt/50"
                      }`}
                    >
                      <div className="flex items-center justify-between w-full mb-3">
                        <div className="flex items-center gap-2">
                          <Moon className="w-4 h-4 text-cobalt" />
                          <span className="font-mono text-xs font-bold uppercase text-navy dark:text-[#F0F4F8]">
                            Dark Mode
                          </span>
                        </div>
                        {theme === "dark" && (
                          <span className="w-2 h-2 rounded-full bg-cobalt" />
                        )}
                      </div>
                      <div className="w-full h-16 rounded bg-[#080F1A] border border-[#1E3652] p-2 flex flex-col justify-between">
                        <div className="w-1/2 h-2 bg-[#F0F4F8] rounded" />
                        <div className="flex gap-1">
                          <div className="w-1/3 h-3 bg-[#101F33] rounded border border-[#1E3652]" />
                          <div className="w-1/4 h-3 bg-[#4D76FF] rounded" />
                        </div>
                      </div>
                      <span className="font-mono text-[10px] text-navy/60 dark:text-[#F0F4F8]/70 mt-2">
                        Obsidian & Cobalt Blueprint
                      </span>
                    </button>

                    {/* System Option */}
                    <button
                      type="button"
                      onClick={() => setTheme("system")}
                      className={`flex flex-col items-start p-4 rounded-[6px] border-2 transition-all cursor-pointer text-left relative ${
                        theme === "system"
                          ? "border-navy dark:border-cobalt bg-ice dark:bg-[#101F33] shadow-[3px_3px_0_0_#0F2B4A] dark:shadow-[3px_3px_0_0_#040910]"
                          : "border-fog dark:border-[#1E3652] bg-white dark:bg-[#0E1A2B] hover:border-navy/50 dark:hover:border-cobalt/50"
                      }`}
                    >
                      <div className="flex items-center justify-between w-full mb-3">
                        <div className="flex items-center gap-2">
                          <Laptop className="w-4 h-4 text-navy/70 dark:text-[#F0F4F8]/70" />
                          <span className="font-mono text-xs font-bold uppercase text-navy dark:text-[#F0F4F8]">
                            System
                          </span>
                        </div>
                        {theme === "system" && (
                          <span className="w-2 h-2 rounded-full bg-navy dark:bg-cobalt" />
                        )}
                      </div>
                      <div className="w-full h-16 rounded bg-gradient-to-r from-[#E8EEF3] to-[#080F1A] border border-fog dark:border-[#1E3652] p-2 flex items-center justify-center">
                        <span className="font-mono text-[10px] font-bold text-navy/80 dark:text-[#F0F4F8] bg-white/80 dark:bg-[#101F33]/80 px-2 py-0.5 rounded">
                          AUTO SYNC
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-navy/60 dark:text-[#F0F4F8]/60 mt-2">
                        Matches your device settings
                      </span>
                    </button>
                  </div>
                </div>

                {/* Sound & Feedback */}
                <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm space-y-4">
                  <div className="flex items-center gap-2.5 mb-1">
                    <Volume2 className="w-5 h-5 text-cobalt" />
                    <h3 className="font-heading text-base font-bold text-navy">
                      Feedback & Sensory Immersion
                    </h3>
                  </div>

                  <div className="flex items-center justify-between py-3 border-b border-fog/60">
                    <div>
                      <div className="font-sans text-sm font-bold text-navy">
                        Keycap Click Sound Effects
                      </div>
                      <div className="font-sans text-xs text-navy/60">
                        Play subtle isometric mechanical clicks when submitting inquiries or pressing keycaps.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={audioForm.soundEffects}
                      onChange={(e) =>
                        setAudioForm({ ...audioForm, soundEffects: e.target.checked })
                      }
                      className="w-5 h-5 accent-cobalt cursor-pointer"
                    />
                  </div>

                  <div className="flex items-center justify-between py-2">
                    <div>
                      <div className="font-sans text-sm font-bold text-navy">
                        Show Reasoning Chain Visualizations
                      </div>
                      <div className="font-sans text-xs text-navy/60">
                        Display the animated 5-stage loop and evaluation pulses during Socratic turns.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={learningForm.showReasoningSteps}
                      onChange={(e) =>
                        setLearningForm({
                          ...learningForm,
                          showReasoningSteps: e.target.checked,
                        })
                      }
                      className="w-5 h-5 accent-cobalt cursor-pointer"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {/* TAB 2: PROFILE & IDENTITY */}
            {activeTab === "profile" && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                {/* Identity Form */}
                <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm space-y-5">
                  <div className="flex items-center gap-2.5 mb-1">
                    <User className="w-5 h-5 text-cobalt" />
                    <h3 className="font-heading text-base font-bold text-navy">
                      Learner Identity & Character Persona
                    </h3>
                  </div>

                  {/* Character Avatar Picker */}
                  <div>
                    <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-2">
                      Feynman Character Avatar
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {[
                        {
                          id: "STUDENT" as CharacterAvatarId,
                          name: "Student",
                          emoji: "🎓",
                          desc: "Curious, asks foundational 'why' questions",
                        },
                        {
                          id: "TEACHER" as CharacterAvatarId,
                          name: "Teacher",
                          emoji: "📐",
                          desc: "Pedagogical guide, checks analogies",
                        },
                        {
                          id: "PROFESSOR" as CharacterAvatarId,
                          name: "Professor",
                          emoji: "⚡",
                          desc: "Evaluates mathematical and logical depth",
                        },
                      ].map((av) => (
                        <button
                          key={av.id}
                          type="button"
                          onClick={() =>
                            setProfileForm({ ...profileForm, characterAvatar: av.id })
                          }
                          className={`p-3 rounded-[6px] border-2 text-left transition-all cursor-pointer ${
                            profileForm.characterAvatar === av.id
                              ? "border-navy bg-ice shadow-[2px_2px_0_0_#0F2B4A]"
                              : "border-fog bg-white hover:border-navy/40"
                          }`}
                        >
                          <div className="text-2xl mb-1">{av.emoji}</div>
                          <div className="font-heading text-xs font-bold text-navy">
                            {av.name}
                          </div>
                          <div className="font-sans text-[11px] text-navy/60">
                            {av.desc}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Display Name & Email */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                    <div>
                      <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-1.5">
                        Display Name
                      </label>
                      <input
                        type="text"
                        value={profileForm.displayName}
                        onChange={(e) =>
                          setProfileForm({
                            ...profileForm,
                            displayName: e.target.value,
                          })
                        }
                        className="w-full px-3.5 py-2 border border-fog rounded-[4px] font-sans text-sm text-navy bg-white focus:border-cobalt focus:outline-none"
                        placeholder="Your full name"
                      />
                    </div>

                    <div>
                      <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-1.5">
                        Email Address
                      </label>
                      <input
                        type="email"
                        value={user?.email || profileForm.email}
                        readOnly
                        className="w-full px-3.5 py-2 border border-fog/80 rounded-[4px] font-mono text-xs text-navy/60 bg-ice/50 cursor-not-allowed"
                      />
                    </div>
                  </div>

                  {/* Role / Occupation */}
                  <div>
                    <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-1.5">
                      Professional Role / Primary Field
                    </label>
                    <input
                      type="text"
                      value={profileForm.role}
                      onChange={(e) =>
                        setProfileForm({ ...profileForm, role: e.target.value })
                      }
                      className="w-full px-3.5 py-2 border border-fog rounded-[4px] font-sans text-sm text-navy bg-white focus:border-cobalt focus:outline-none"
                      placeholder="e.g. AI Engineer, Physics Student, Data Scientist"
                    />
                  </div>

                  {/* Learning Goal */}
                  <div>
                    <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-1.5">
                      Current Learning Target
                    </label>
                    <input
                      type="text"
                      value={profileForm.learningGoal}
                      onChange={(e) =>
                        setProfileForm({
                          ...profileForm,
                          learningGoal: e.target.value,
                        })
                      }
                      className="w-full px-3.5 py-2 border border-fog rounded-[4px] font-sans text-sm text-navy bg-white focus:border-cobalt focus:outline-none"
                      placeholder="e.g. Master Neural Architecture and Quantum Algorithms"
                    />
                  </div>

                  {/* Bio */}
                  <div>
                    <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-1.5">
                      Personal Feynman Philosophy / Bio
                    </label>
                    <textarea
                      rows={3}
                      value={profileForm.bio}
                      onChange={(e) =>
                        setProfileForm({ ...profileForm, bio: e.target.value })
                      }
                      className="w-full px-3.5 py-2 border border-fog rounded-[4px] font-sans text-sm text-navy bg-white focus:border-cobalt focus:outline-none resize-none"
                      placeholder="Brief note about what drives your learning inquiry..."
                    />
                  </div>
                </div>

                {/* Rank & Stats Summary */}
                <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Award className="w-5 h-5 text-gap-orange" />
                      <h4 className="font-heading text-sm font-bold text-navy uppercase">
                        Mastery Tier & Achievements
                      </h4>
                    </div>
                    <span className="font-mono text-xs font-bold text-cobalt bg-ice px-2 py-0.5 rounded border border-fog">
                      TIER: {profile.levelTitle}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                    <div className="p-3 bg-ice/50 rounded-[4px] border border-fog/60">
                      <div className="font-mono text-xl font-bold text-gap-orange">
                        {stats.gapsResolved}
                      </div>
                      <div className="font-mono text-[10px] uppercase text-navy/60">
                        Gaps Resolved
                      </div>
                    </div>
                    <div className="p-3 bg-ice/50 rounded-[4px] border border-fog/60">
                      <div className="font-mono text-xl font-bold text-cobalt">
                        {stats.conceptsMastered}
                      </div>
                      <div className="font-mono text-[10px] uppercase text-navy/60">
                        Concepts Mastered
                      </div>
                    </div>
                    <div className="p-3 bg-ice/50 rounded-[4px] border border-fog/60">
                      <div className="font-mono text-xl font-bold text-navy">
                        {stats.totalSessions}
                      </div>
                      <div className="font-mono text-[10px] uppercase text-navy/60">
                        Sessions Completed
                      </div>
                    </div>
                    <div className="p-3 bg-ice/50 rounded-[4px] border border-fog/60">
                      <div className="font-mono text-xl font-bold text-navy">
                        {stats.voiceMinutes}m
                      </div>
                      <div className="font-mono text-[10px] uppercase text-navy/60">
                        Voice Dialogue
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* TAB 3: FEYNMAN LABORATORY */}
            {activeTab === "learning" && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                {/* Socratic Rigor Level */}
                <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm space-y-5">
                  <div className="flex items-center gap-2.5 mb-1">
                    <Sliders className="w-5 h-5 text-gap-orange" />
                    <h3 className="font-heading text-base font-bold text-navy">
                      Feynman Inquiry Rigor & Evaluation Mode
                    </h3>
                  </div>
                  <p className="font-sans text-xs text-navy/70">
                    Controls how aggressively Curio questions your terminology, detects buzzwords, and tests edge cases during student and teacher dialogues.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {[
                      {
                        id: "gentle" as FeynmanRigorLevel,
                        title: "Gentle Coach",
                        tag: "BEGINNER SAFE",
                        desc: "Validates high-level intuition, provides hints when stuck, and accepts simplified analogies.",
                      },
                      {
                        id: "socratic" as FeynmanRigorLevel,
                        title: "Socratic Challenger",
                        tag: "RECOMMENDED",
                        desc: "Probes edge cases, detects hand-waving, and asks targeted questions to isolate missing links.",
                      },
                      {
                        id: "rigorous" as FeynmanRigorLevel,
                        title: "Rigorous Feynman",
                        tag: "ADVANCED",
                        desc: "Rejects ungrounded jargon completely. Requires exact first-principles explanations from atomic axioms.",
                      },
                    ].map((mode) => (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() =>
                          setLearningForm({ ...learningForm, rigorLevel: mode.id })
                        }
                        className={`p-4 rounded-[6px] border-2 text-left transition-all cursor-pointer flex flex-col justify-between ${
                          learningForm.rigorLevel === mode.id
                            ? "border-navy bg-ice shadow-[3px_3px_0_0_#0F2B4A]"
                            : "border-fog bg-white hover:border-navy/40"
                        }`}
                      >
                        <div>
                          <span
                            className={`font-mono text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                              mode.id === "socratic"
                                ? "bg-gap-orange text-white"
                                : "bg-ice text-navy/60 border border-fog"
                            }`}
                          >
                            {mode.tag}
                          </span>
                          <h4 className="font-heading text-sm font-bold text-navy mt-2 mb-1">
                            {mode.title}
                          </h4>
                          <p className="font-sans text-xs text-navy/70 leading-relaxed">
                            {mode.desc}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>

                  {/* Probing Depth Slider */}
                  <div className="pt-4 border-t border-fog/60">
                    <div className="flex justify-between items-center mb-2">
                      <label className="font-mono text-xs font-bold uppercase text-navy">
                        Inquiry Probing Depth ({learningForm.probingDepth} Layers)
                      </label>
                      <span className="font-mono text-xs text-cobalt font-bold">
                        {learningForm.probingDepth === 1 && "Surface Verification"}
                        {learningForm.probingDepth === 2 && "Moderate Inquiry"}
                        {learningForm.probingDepth === 3 && "Standard Multi-Turn"}
                        {learningForm.probingDepth === 4 && "Deep First-Principles"}
                        {learningForm.probingDepth === 5 && "Exhaustive Axiomatic"}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={5}
                      step={1}
                      value={learningForm.probingDepth}
                      onChange={(e) =>
                        setLearningForm({
                          ...learningForm,
                          probingDepth: parseInt(e.target.value, 10),
                        })
                      }
                      className="w-full accent-cobalt cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] font-mono text-navy/40 mt-1">
                      <span>1: Brief</span>
                      <span>3: Standard</span>
                      <span>5: Maximum Depth</span>
                    </div>
                  </div>

                  {/* Auto-generate Gap Report */}
                  <div className="flex items-center justify-between pt-3 border-t border-fog/60">
                    <div>
                      <div className="font-sans text-sm font-bold text-navy">
                        Auto-generate 3D Gap Report on Session End
                      </div>
                      <div className="font-sans text-xs text-navy/60">
                        Automatically synthesize knowledge topology and render interactive map when finishing chat or audio.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={learningForm.autoGenerateReport}
                      onChange={(e) =>
                        setLearningForm({
                          ...learningForm,
                          autoGenerateReport: e.target.checked,
                        })
                      }
                      className="w-5 h-5 accent-cobalt cursor-pointer"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {/* TAB 4: VOICE & AUDIO */}
            {activeTab === "audio" && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                {/* Voice Selection */}
                <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm space-y-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Mic className="w-5 h-5 text-cobalt" />
                      <h3 className="font-heading text-base font-bold text-navy">
                        Voice Persona & Speech Studio
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={handlePlayVoiceSample}
                      disabled={isPlayingTestVoice}
                      className="inline-flex items-center gap-1.5 px-3 py-1 bg-ice border border-fog hover:bg-white text-navy rounded-[4px] font-mono text-xs font-bold transition-all shadow-xs cursor-pointer"
                    >
                      <Volume2 className="w-3.5 h-3.5 text-cobalt" />
                      <span>{isPlayingTestVoice ? "PLAYING..." : "TEST VOICE SAMPLE"}</span>
                    </button>
                  </div>

                  <div>
                    <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-2">
                      Active Voice Persona
                    </label>
                    <select
                      value={audioForm.voicePersona}
                      onChange={(e) =>
                        setAudioForm({ ...audioForm, voicePersona: e.target.value })
                      }
                      className="w-full px-3.5 py-2 border border-fog rounded-[4px] font-sans text-sm text-navy bg-white focus:border-cobalt focus:outline-none"
                    >
                      <option value="Curio Feynman (Enthusiastic & Deep)">
                        Curio Feynman (Enthusiastic & Deep)
                      </option>
                      <option value="Curio Nova (Clear & Analytical)">
                        Curio Nova (Clear & Analytical)
                      </option>
                      <option value="Curio Ada (Calm & Socratic)">
                        Curio Ada (Calm & Socratic)
                      </option>
                      <option value="Curio Socrates (Philosophical & Inquisitive)">
                        Curio Socrates (Philosophical & Inquisitive)
                      </option>
                    </select>
                  </div>

                  {/* Speech Rate Slider */}
                  <div className="pt-2">
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="font-mono text-xs font-bold uppercase text-navy">
                        Speech Rate ({audioForm.speechRate.toFixed(2)}x)
                      </label>
                      <span className="font-mono text-xs text-cobalt font-semibold">
                        {audioForm.speechRate < 1
                          ? "Slow & Deliberate"
                          : audioForm.speechRate > 1.1
                          ? "Brisk & Energetic"
                          : "Natural Cadence"}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={0.8}
                      max={1.4}
                      step={0.05}
                      value={audioForm.speechRate}
                      onChange={(e) =>
                        setAudioForm({
                          ...audioForm,
                          speechRate: parseFloat(e.target.value),
                        })
                      }
                      className="w-full accent-cobalt cursor-pointer"
                    />
                  </div>

                  {/* Auto-play spoken audio */}
                  <div className="flex items-center justify-between pt-3 border-t border-fog/60">
                    <div>
                      <div className="font-sans text-sm font-bold text-navy">
                        Auto-Play Character Voice Responses
                      </div>
                      <div className="font-sans text-xs text-navy/60">
                        Immediately speak the character's reply when receiving WebSocket turns in voice mode.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={audioForm.autoPlayAudio}
                      onChange={(e) =>
                        setAudioForm({
                          ...audioForm,
                          autoPlayAudio: e.target.checked,
                        })
                      }
                      className="w-5 h-5 accent-cobalt cursor-pointer"
                    />
                  </div>

                  {/* Noise cancellation */}
                  <div className="flex items-center justify-between py-2 border-t border-fog/60">
                    <div>
                      <div className="font-sans text-sm font-bold text-navy">
                        Background Noise Suppression
                      </div>
                      <div className="font-sans text-xs text-navy/60">
                        Filter out fan noise and ambient keyboard clicks during spoken explanation turns.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={audioForm.noiseCancellation}
                      onChange={(e) =>
                        setAudioForm({
                          ...audioForm,
                          noiseCancellation: e.target.checked,
                        })
                      }
                      className="w-5 h-5 accent-cobalt cursor-pointer"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {/* TAB 5: DATA, EXPORT & PRIVACY */}
            {activeTab === "privacy" && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                {/* Data Export Card */}
                <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm space-y-4">
                  <div className="flex items-center gap-2.5 mb-1">
                    <Download className="w-5 h-5 text-cobalt" />
                    <h3 className="font-heading text-base font-bold text-navy">
                      Export Laboratory History & Knowledge Maps
                    </h3>
                  </div>
                  <p className="font-sans text-xs text-navy/70">
                    Download your complete learning records, concepts mastered, and gap reports in portable, structured JSON format.
                  </p>

                  <div className="flex flex-wrap gap-3 pt-2">
                    <KeycapButton
                      variant="navy"
                      size="sm"
                      onClick={handleExportData}
                      className="gap-2"
                    >
                      <Download className="w-3.5 h-3.5" />
                      EXPORT AS JSON
                    </KeycapButton>
                  </div>
                </div>

                {/* Reset & Danger Zone */}
                <div className="bg-white border-2 border-rose-200 rounded-[6px] p-6 shadow-sm space-y-4">
                  <div className="flex items-center gap-2.5 text-rose-700">
                    <Trash2 className="w-5 h-5" />
                    <h3 className="font-heading text-base font-bold">
                      Laboratory Reset & Cache Management
                    </h3>
                  </div>
                  <p className="font-sans text-xs text-navy/70">
                    Reset your local preferences, audio calibrations, and inquiry sensitivity back to default factory settings.
                  </p>

                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (
                          confirm(
                            "Are you sure you want to reset all preferences to default?"
                          )
                        ) {
                          resetToDefaults();
                          curioToast.success("Reset Complete", "All preferences have been restored to defaults.");
                        }
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] font-mono text-xs font-bold text-rose-700 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 border border-rose-300 transition-colors cursor-pointer"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>RESET PREFERENCES TO DEFAULTS</span>
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* TAB 6: API KEYS & POWER USER */}
            {activeTab === "api" && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm space-y-5">
                  <div className="flex items-center gap-2.5 mb-1">
                    <Key className="w-5 h-5 text-cobalt" />
                    <h3 className="font-heading text-base font-bold text-navy">
                      Custom AI Model Keys (Optional)
                    </h3>
                  </div>
                  <p className="font-sans text-xs text-navy/70">
                    Curio comes with built-in backend inference out of the box. Power users can supply their own Google Gemini or ElevenLabs keys for unlimited personal quota.
                  </p>

                  {/* Gemini Key */}
                  <div>
                    <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-1.5">
                      Google Gemini API Key
                    </label>
                    <div className="relative">
                      <input
                        type={showGeminiKey ? "text" : "password"}
                        value={privacyForm.customGeminiApiKey}
                        onChange={(e) =>
                          setPrivacyForm({
                            ...privacyForm,
                            customGeminiApiKey: e.target.value,
                          })
                        }
                        className="w-full px-3.5 py-2 pr-10 border border-fog rounded-[4px] font-mono text-xs text-navy bg-white focus:border-cobalt focus:outline-none"
                        placeholder="AIzaSy..."
                      />
                      <button
                        type="button"
                        onClick={() => setShowGeminiKey((prev) => !prev)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-navy/40 hover:text-navy cursor-pointer"
                      >
                        {showGeminiKey ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* ElevenLabs Key */}
                  <div>
                    <label className="font-mono text-xs font-bold uppercase text-navy/70 block mb-1.5">
                      ElevenLabs Voice API Key (Optional)
                    </label>
                    <input
                      type="password"
                      value={privacyForm.customElevenLabsApiKey}
                      onChange={(e) =>
                        setPrivacyForm({
                          ...privacyForm,
                          customElevenLabsApiKey: e.target.value,
                        })
                      }
                      className="w-full px-3.5 py-2 border border-fog rounded-[4px] font-mono text-xs text-navy bg-white focus:border-cobalt focus:outline-none"
                      placeholder="sk_..."
                    />
                  </div>

                  <div className="p-3 bg-ice/60 border border-fog/80 rounded-[4px] text-xs font-mono text-navy/70 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-gap-orange shrink-0" />
                    <span>Keys are stored strictly locally in your browser session.</span>
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-ice text-navy flex items-center justify-center font-mono text-xs uppercase tracking-widest">
          <span className="animate-spin text-cobalt text-base mr-2">◈</span>
          Loading Settings...
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}
