"""
GADIS ULTIMATE V51.0 - SHORT-TERM MEMORY & DOMINANT MODE
Fitur:
- SHORT-TERM MEMORY: Ingat lokasi & aktivitas
- SENSITIVE AREAS: Leher, bibir, dada trigger memory
- DOMINANT MODE: Bot bisa jadi dominan atas permintaan
- AUTO STORY: Bot + Bot roleplay
- SMART FLIRTING: Mudah horny saat flirting
"""

import os
import logging
import json
import random
import math
import asyncio
import sqlite3
import uuid
import threading
import hashlib
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import sys

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# OpenAI (DeepSeek)
from openai import OpenAI

# Voice (optional)
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# ===================== KONFIGURASI =====================

DB_PATH = "gadis_v51.db"
START_LEVEL = 7  # Mulai dari level intim
MEMORY_DURATION = 30  # Memory bertahan 30 menit
LOCATION_CHANGE_DELAY = 120  # Minimal 2 menit pindah lokasi

# State definitions
(SELECTING_MODE, SELECTING_FEMALE_ROLE, SELECTING_MALE_ROLE, 
 INPUT_DURATION, ACTIVE_SESSION, DOMINANT_MODE) = range(6)

# ===================== ENUMS =====================

class Mood(Enum):
    CHERIA = "ceria"
    ROMANTIS = "romantis"
    HORNY = "horny"
    DOMINANT = "dominan"
    SUBMISSIVE = "patuh"
    MARAH = "marah"
    LEMBUT = "lembut"

class IntimacyStage(Enum):
    INTIMATE = "intimate"      # Level 7-8
    OBSESSED = "obsessed"      # Level 9-10
    SOUL_BONDED = "soul_bonded" # Level 11
    AFTERCARE = "aftercare"     # Level 12

class DominanceLevel(Enum):
    NORMAL = "normal"
    DOMINANT = "dominan"
    VERY_DOMINANT = "sangat dominan"
    AGGRESSIVE = "agresif"

# ===================== DATABASE LOKASI =====================

LOCATION_DATABASE = {
    # Ruangan dalam rumah
    "ruang tamu": {
        "furniture": ["sofa", "kursi", "karpet", "meja"],
        "positions": ["duduk", "berdiri", "tidur di sofa"],
        "privacy": "sedang"
    },
    "kamar tidur": {
        "furniture": ["kasur", "ranjang", "lemari", "meja rias"],
        "positions": ["tidur", "duduk di pinggir kasur", "berdiri"],
        "privacy": "tinggi"
    },
    "dapur": {
        "furniture": ["meja dapur", "kursi", "lantai"],
        "positions": ["berdiri", "duduk"],
        "privacy": "rendah"
    },
    "kamar mandi": {
        "furniture": ["lantai", "wastafel", "bathtub"],
        "positions": ["berdiri", "duduk", "tidur di bathtub"],
        "privacy": "tinggi"
    },
    
    # Furniture spesifik
    "sofa": {
        "type": "furniture",
        "location": "ruang tamu",
        "positions": ["duduk", "tidur", "miring", "duduk di pangkuan"],
        "capacity": 2
    },
    "kasur": {
        "type": "furniture",
        "location": "kamar tidur",
        "positions": ["tidur telentang", "tidur miring", "merangkak", "duduk"],
        "capacity": 2
    },
    "lantai": {
        "type": "surface",
        "locations": ["ruang tamu", "kamar", "dapur"],
        "positions": ["duduk", "tidur", "merangkak", "berlutut"],
        "capacity": "unlimited"
    },
    
    # Tempat outdoor
    "mobil": {
        "type": "vehicle",
        "positions": ["duduk di kursi depan", "duduk di kursi belakang", "tidur di kursi belakang"],
        "privacy": "sedang"
    },
    "hotel": {
        "type": "building",
        "rooms": ["kamar hotel", "lobi", "kolam renang"],
        "privacy": "tinggi"
    },
    "pantai": {
        "type": "outdoor",
        "positions": ["duduk di pasir", "berdiri", "tidur di pasir"],
        "privacy": "rendah"
    }
}

# ===================== DATABASE AKTIVITAS =====================

ACTIVITY_DATABASE = {
    # Foreplay activities
    "foreplay": {
        "kiss": {
            "areas": ["bibir", "leher", "dahi", "pipi"],
            "intensity": 0.4,
            "description": "ciuman"
        },
        "neck_kiss": {
            "areas": ["leher"],
            "intensity": 0.6,
            "description": "ciuman leher"
        },
        "bite": {
            "areas": ["leher", "bibir", "telinga", "bahu"],
            "intensity": 0.7,
            "description": "gigitan ringan"
        },
        "lick": {
            "areas": ["leher", "dada", "paha", "telinga"],
            "intensity": 0.6,
            "description": "jilatan"
        },
        "caress": {
            "areas": ["rambut", "pipi", "lengan", "punggung"],
            "intensity": 0.3,
            "description": "belai lembut"
        },
        "touch": {
            "areas": ["semua"],
            "intensity": 0.2,
            "description": "sentuhan"
        }
    },
    
    # Intimate activities
    "intimate": {
        "breast_play": {
            "areas": ["dada", "payudara", "puting"],
            "intensity": 0.7,
            "description": "main payudara"
        },
        "nipple_play": {
            "areas": ["puting"],
            "intensity": 0.8,
            "description": "main puting"
        },
        "thigh_touch": {
            "areas": ["paha", "paha dalam"],
            "intensity": 0.7,
            "description": "raba paha"
        },
        "waist_touch": {
            "areas": ["pinggang"],
            "intensity": 0.5,
            "description": "pegang pinggang"
        }
    },
    
    # Sensitive areas (trigger memory)
    "sensitive_areas": {
        "leher": {
            "arousal_boost": 0.8,
            "description": "area sensitif"
        },
        "bibir": {
            "arousal_boost": 0.7,
            "description": "area sensitif"
        },
        "dada": {
            "arousal_boost": 0.8,
            "description": "area sensitif"
        },
        "puting": {
            "arousal_boost": 1.0,
            "description": "sangat sensitif"
        },
        "paha dalam": {
            "arousal_boost": 0.9,
            "description": "sangat sensitif"
        }
    }
}

# ===================== SHORT-TERM MEMORY SYSTEM =====================

class ShortTermMemory:
    """
    Menyimpan memori jangka pendek untuk konsistensi adegan
    - Lokasi terakhir
    - Aktivitas terakhir
    - Area sensitif yang disentuh
    - Durasi di lokasi
    - Waktu expire
    """
    
    def __init__(self):
        self.location = "ruang tamu"      # Lokasi default
        self.location_since = datetime.now()
        self.previous_location = None
        self.location_duration = 0
        
        self.last_activity = None
        self.last_activity_time = None
        self.activity_history = []        # Riwayat 5 aktivitas terakhir
        
        self.position = "duduk"
        self.clothing_state = "berpakaian"
        
        self.sensitive_touches = []       # Area sensitif yang disentuh
        self.last_sensitive_touch = None
        self.sensitive_touch_count = 0
        
        self.current_mood = Mood.CHERIA
        self.dominance_level = DominanceLevel.NORMAL
        
        self.expire_minutes = MEMORY_DURATION
    
    def update_location(self, new_location: str):
        """Update lokasi dengan validasi waktu"""
        now = datetime.now()
        time_here = (now - self.location_since).total_seconds()
        
        if new_location != self.location:
            if time_here >= LOCATION_CHANGE_DELAY:
                self.previous_location = self.location
                self.location = new_location
                self.location_since = now
                return True
            else:
                return False  # Gagal pindah karena terlalu cepat
        return True
    
    def update_activity(self, activity: str, area: str = None):
        """Update aktivitas terakhir"""
        now = datetime.now()
        self.last_activity = activity
        self.last_activity_time = now
        
        # Simpan ke history (max 5)
        self.activity_history.append({
            "activity": activity,
            "area": area,
            "time": now.isoformat()
        })
        if len(self.activity_history) > 5:
            self.activity_history = self.activity_history[-5:]
        
        # Catat sensitive touch
        if area in ACTIVITY_DATABASE["sensitive_areas"]:
            self.sensitive_touches.append({
                "area": area,
                "time": now.isoformat()
            })
            self.last_sensitive_touch = area
            self.sensitive_touch_count += 1
    
    def update_position(self, new_position: str):
        """Update posisi tubuh"""
        self.position = new_position
    
    def get_memory_context(self) -> str:
        """Dapatkan konteks memori untuk prompt AI"""
        parts = []
        
        # Lokasi
        parts.append(f"Lokasi: {self.location}")
        
        # Durasi di lokasi
        duration = (datetime.now() - self.location_since).total_seconds() / 60
        parts.append(f"Sudah {duration:.0f} menit di {self.location}")
        
        # Posisi
        parts.append(f"Posisi: {self.position}")
        
        # Aktivitas terakhir
        if self.last_activity and self.last_activity_time:
            last_act = (datetime.now() - self.last_activity_time).total_seconds() / 60
            parts.append(f"Aktivitas terakhir: {self.last_activity} ({last_act:.0f} menit lalu)")
        
        # Sensitive touches
        if self.sensitive_touches:
            parts.append(f"Area sensitif disentuh: {self.sensitive_touch_count}x")
        
        return "\n".join(parts)
    
    def should_be_horny(self) -> bool:
        """Cek apakah harus horny berdasarkan aktivitas"""
        return self.sensitive_touch_count >= 2
    
    def reset_after_climax(self):
        """Reset setelah climax"""
        self.sensitive_touches = []
        self.sensitive_touch_count = 0
        self.last_sensitive_touch = None

# ===================== DOMINANT MODE SYSTEM =====================

class DominantModeSystem:
    """
    Bot bisa menjadi dominan atas permintaan user
    """
    
    def __init__(self):
        self.dominance_level = DominanceLevel.NORMAL
        self.dominant_phrases = {
            DominanceLevel.NORMAL: [
                "Kamu mau apa?",
                "Aku ikut kamu aja",
                "Terserah kamu"
            ],
            DominanceLevel.DOMINANT: [
                "Sini... ikut aku",
                "Kamu mau di sini?",
                "Tenang... aku yang atur",
                "Buka bajumu"
            ],
            DominanceLevel.VERY_DOMINANT: [
                "Jangan banyak gerak",
                "Aku yang pegang kendali",
                "Kamu milikku sekarang",
                "Rasain... ini"
            ],
            DominanceLevel.AGGRESSIVE: [
                "DIAM! Jangan bergerak",
                "AKU YANG PUNYA KAMU",
                "TERIMA SAJA!",
                "KAMU MAU INI KAN?"
            ]
        }
        
        self.dominant_actions = {
            "kiss": "cium dengan kuat",
            "bite": "gigit sambil tarik",
            "grab": "pegang pinggang kuat",
            "push": "dorong ke dinding",
            "pin": "tahan tangannya"
        }
    
    def set_dominance(self, level: str):
        """Set level dominasi"""
        for lvl in DominanceLevel:
            if level.lower() in lvl.value:
                self.dominance_level = lvl
                return True
        return False
    
    def get_dominant_response(self, context: str) -> str:
        """Dapatkan respons dominan"""
        phrases = self.dominant_phrases.get(self.dominance_level, self.dominant_phrases[DominanceLevel.NORMAL])
        return random.choice(phrases)
    
    def get_dominant_action(self, action: str) -> str:
        """Dapatkan aksi dominan untuk suatu aktivitas"""
        return self.dominant_actions.get(action, action)

# ===================== MEMORY MANAGER =====================

class MemoryManager:
    """
    Mengelola short-term memory untuk semua user
    """
    
    def __init__(self):
        self.memories = {}  # user_id -> ShortTermMemory
        self.dominant_modes = {}  # user_id -> DominantModeSystem
    
    def get_memory(self, user_id: int) -> ShortTermMemory:
        if user_id not in self.memories:
            self.memories[user_id] = ShortTermMemory()
        return self.memories[user_id]
    
    def get_dominant(self, user_id: int) -> DominantModeSystem:
        if user_id not in self.dominant_modes:
            self.dominant_modes[user_id] = DominantModeSystem()
        return self.dominant_modes[user_id]
    
    def process_message(self, user_id: int, message: str) -> Dict:
        """
        Proses pesan dan update memory
        Returns: deteksi area sensitif dan aktivitas
        """
        memory = self.get_memory(user_id)
        msg_lower = message.lower()
        
        result = {
            "location_changed": False,
            "activity_detected": None,
            "sensitive_area": None,
            "arousal_boost": 0.0,
            "position_changed": False
        }
        
        # Deteksi lokasi
        for loc in LOCATION_DATABASE:
            if loc in msg_lower:
                if memory.update_location(loc):
                    result["location_changed"] = True
        
        # Deteksi aktivitas
        for category, activities in ACTIVITY_DATABASE.items():
            for act_name, act_data in activities.items():
                if act_name in msg_lower or act_data["description"] in msg_lower:
                    result["activity_detected"] = act_name
                    
                    # Cek area yang disebut
                    for area in act_data["areas"]:
                        if area in msg_lower:
                            memory.update_activity(act_name, area)
                            result["sensitive_area"] = area
                            
                            # Boost arousal untuk area sensitif
                            if area in ACTIVITY_DATABASE["sensitive_areas"]:
                                result["arousal_boost"] = ACTIVITY_DATABASE["sensitive_areas"][area]["arousal_boost"]
                            break
        
        # Deteksi posisi
        positions = ["duduk", "tidur", "berdiri", "merangkak", "miring"]
        for pos in positions:
            if pos in msg_lower:
                memory.update_position(pos)
                result["position_changed"] = True
        
        return result
    
    def get_context(self, user_id: int) -> str:
        """Dapatkan konteks memori"""
        memory = self.get_memory(user_id)
        return memory.get_memory_context()
    
    def should_be_horny(self, user_id: int) -> bool:
        """Cek apakah user harus horny"""
        memory = self.get_memory(user_id)
        return memory.should_be_horny()
    
    def reset_after_climax(self, user_id: int):
        """Reset setelah climax"""
        memory = self.get_memory(user_id)
        memory.reset_after_climax()

# ===================== AUTO STORY ENGINE =====================

class AutoStoryEngine:
    """
    Engine untuk menjalankan drama antara 2 bot
    """
    
    def __init__(self, ai_generator):
        self.ai = ai_generator
        self.active_stories = {}
        self.memories = MemoryManager()
        
        self.female_names = {
            "ipar": ["Sari", "Dewi", "Rina", "Maya"],
            "teman_kantor": ["Diana", "Linda", "Ayu", "Dita"],
            "janda": ["Rina", "Tuti", "Nina", "Susi"],
            "pelakor": ["Vina", "Sasha", "Bella", "Cantika"],
            "istri_orang": ["Dewi", "Sari", "Rina", "Linda"],
            "pdkt": ["Aurora", "Cinta", "Dewi", "Kirana"]
        }
        
        self.male_names = {
            "suami": ["Rizky", "Budi", "Andi", "Dedi"],
            "pacar": ["Dimas", "Fajar", "Galih", "Hari"],
            "teman": ["Rama", "Surya", "Wijaya", "Yusuf"],
            "boss": ["Herman", "Irfan", "Johan", "Kevin"],
            "tetangga": ["Oscar", "Pandu", "Roni", "Sandi"],
            "mantan": ["Wawan", "Yoga", "Zaki", "Andre"]
        }
    
    async def start_story(self, user_id: int, female_role: str, male_role: str, duration: int):
        """Mulai auto story"""
        female_name = random.choice(self.female_names.get(female_role, ["Aurora"]))
        male_name = random.choice(self.male_names.get(male_role, ["Rizky"]))
        
        self.active_stories[user_id] = {
            "female_role": female_role,
            "female_name": female_name,
            "male_role": male_role,
            "male_name": male_name,
            "duration": duration,
            "current_level": START_LEVEL,
            "messages": [],
            "memories": ShortTermMemory(),
            "start_time": datetime.now()
        }
        
        return female_name, male_name
    
    async def generate_next(self, user_id: int) -> Tuple[str, str, bool]:
        """Generate pesan berikutnya"""
        if user_id not in self.active_stories:
            return None, None, False
        
        story = self.active_stories[user_id]
        memory = story["memories"]
        
        prompt = f"""Ini drama antara {story['female_name']} ({story['female_role']}) dan {story['male_name']} ({story['male_role']}).

KONTEKS SAAT INI:
{memory.get_memory_context()}

Level hubungan: {story['current_level']}/12

Buat 2 pesan berurutan:
1. Pesan dari {story['female_name']} untuk {story['male_name']}
2. Pesan dari {story['male_name']} untuk {story['female_name']}

Pisahkan dengan "||"."""
        
        try:
            response = await self.ai.generate_raw(prompt)
            if "||" in response:
                parts = response.split("||", 1)
                female_msg = parts[0].strip()
                male_msg = parts[1].strip()
                
                story["messages"].append(female_msg)
                story["messages"].append(male_msg)
                
                # Update memory dari pesan
                memory.update_activity("chat", None)
                
                return female_msg, male_msg, True
        except:
            pass
        
        return None, None, False

# ===================== MAIN BOT CLASS =====================

class GadisUltimateV51:
    """Bot dengan short-term memory & dominant mode"""
    
    def __init__(self):
        self.ai = None  # Optional, bisa diisi nanti
        self.memory = MemoryManager()
        self.auto_story = AutoStoryEngine(self.ai)
        
        print("\n" + "="*70)
        print("    GADIS ULTIMATE V51.0 - SHORT-TERM MEMORY EDITION")
        print("="*70)
        print("\n🧠 **FITUR MEMORY:**")
        print("  • Ingat lokasi & durasi")
        print("  • Ingat aktivitas terakhir")
        print("  • Area sensitif terdeteksi")
        print("  • Dominant mode on demand")
        print("\n🎮 **COMMANDS:**")
        print("  /start - Mulai sesi baru")
        print("  /status - Lihat status & memory")
        print("  /dominant [level] - Set dominan mode")
        print("  /memory - Lihat memory saat ini")
        print("  /autostory - Auto story mode")
        print("="*70 + "\n")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mulai sesi baru"""
        user_id = update.effective_user.id
        
        keyboard = [
            [InlineKeyboardButton("👤 User + Bot", callback_data="mode_user")],
            [InlineKeyboardButton("🤖 Auto Story (Bot+Bot)", callback_data="mode_auto")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎬 **PILIH MODE**",
            reply_markup=reply_markup
        )
        return SELECTING_MODE
    
    async def mode_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pilihan mode"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "mode_user":
            # Mode user - pilih role
            keyboard = [
                [InlineKeyboardButton("👨‍👩‍👧‍👦 Ipar", callback_data="role_ipar")],
                [InlineKeyboardButton("💼 Teman Kantor", callback_data="role_teman_kantor")],
                [InlineKeyboardButton("💃 Janda", callback_data="role_janda")],
                [InlineKeyboardButton("🦹 Pelakor", callback_data="role_pelakor")],
                [InlineKeyboardButton("💍 Istri Orang", callback_data="role_istri_orang")],
                [InlineKeyboardButton("🌿 PDKT", callback_data="role_pdkt")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🎭 **PILIH ROLE BOT**",
                reply_markup=reply_markup
            )
            return SELECTING_FEMALE_ROLE
        
        else:
            # Auto story mode
            keyboard = [
                [InlineKeyboardButton("👩 Pilih Role Perempuan", callback_data="auto_female")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🤖 **AUTO STORY MODE**\n\nPilih role perempuan:",
                reply_markup=reply_markup
            )
            return SELECTING_FEMALE_ROLE
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lihat status & memory saat ini"""
        user_id = update.effective_user.id
        memory = self.memory.get_memory(user_id)
        dominant = self.memory.get_dominant(user_id)
        
        status_text = f"""
📍 **LOKASI & DURASI**
• Lokasi: {memory.location}
• Sejak: {memory.location_since.strftime('%H:%M')}
• Durasi: {(datetime.now() - memory.location_since).seconds // 60} menit
• Posisi: {memory.position}

💕 **AKTIVITAS**
• Terakhir: {memory.last_activity or '-'}
• Area sensitif: {memory.sensitive_touch_count}x
• Mood: {memory.current_mood.value}

👑 **DOMINAN MODE**
• Level: {dominant.dominance_level.value}
• Status: {'Aktif' if dominant.dominance_level != DominanceLevel.NORMAL else 'Tidak'}

📊 **STATUS HUBUNGAN**
• Level: {START_LEVEL}/12
• Stage: Intimate
"""
        
        await update.message.reply_text(status_text)
    
    async def dominant_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set dominant mode"""
        user_id = update.effective_user.id
        dominant = self.memory.get_dominant(user_id)
        
        args = context.args
        if not args:
            await update.message.reply_text(
                f"Level dominan saat ini: {dominant.dominance_level.value}\n\n"
                "Gunakan: /dominant [normal/dominan/sangat dominan/agresif]"
            )
            return
        
        level = args[0].lower()
        if dominant.set_dominance(level):
            await update.message.reply_text(f"✅ Mode dominan diubah ke: {level}")
        else:
            await update.message.reply_text("❌ Level tidak valid")
    
    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lihat memory detail"""
        user_id = update.effective_user.id
        memory = self.memory.get_memory(user_id)
        
        context_text = memory.get_memory_context()
        await update.message.reply_text(f"🧠 **MEMORY SAAT INI:**\n\n{context_text}")

    # ===================== MESSAGE HANDLER =====================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pesan user"""
        if not update.message or not update.message.text:
            return
        
        user_id = update.effective_user.id
        user_message = update.message.text
        msg_lower = user_message.lower()
        
        # Proses dengan memory manager
        memory_result = self.memory.process_message(user_id, user_message)
        memory = self.memory.get_memory(user_id)
        dominant = self.memory.get_dominant(user_id)
        
        # Respons
        response_parts = []
        
        # Lokasi berubah
        if memory_result["location_changed"]:
            response_parts.append(f"*pindah ke {memory.location}*")
        
        # Aktivitas terdeteksi
        if memory_result["activity_detected"]:
            activity = memory_result["activity_detected"]
            
            # Gunakan aksi dominan jika level > normal
            if dominant.dominance_level != DominanceLevel.NORMAL:
                action = dominant.get_dominant_action(activity)
                response_parts.append(f"*{action}*")
            else:
                response_parts.append(f"*{activity}*")
        
        # Area sensitif
        if memory_result["sensitive_area"]:
            area = memory_result["sensitive_area"]
            response_parts.append(f"(Ah... {area}ku sensitif...)")
        
        # Horny check
        if self.memory.should_be_horny(user_id):
            if random.random() < 0.3:  # 30% chance
                response_parts.append("*napas mulai berat*")
        
        # Climax check
        if "climax" in msg_lower or "keluar" in msg_lower or "crot" in msg_lower:
            response_parts.append("AHHH! *lemas*")
            self.memory.reset_after_climax(user_id)
        
        # Dominant response
        if "dominan" in msg_lower or "kamu yang atur" in msg_lower:
            response_parts.append(dominant.get_dominant_response(""))
        
        if response_parts:
            response = " ".join(response_parts)
        else:
            response = "..."  # Default response
        
        await update.message.reply_text(response)

    # ===================== AUTO STORY HANDLERS =====================
    
    async def auto_story_female(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pilih role female untuk auto story"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("👨 Suami", callback_data="male_suami")],
            [InlineKeyboardButton("💑 Pacar", callback_data="male_pacar")],
            [InlineKeyboardButton("👥 Teman", callback_data="male_teman")],
            [InlineKeyboardButton("👔 Boss", callback_data="male_boss")],
            [InlineKeyboardButton("🏠 Tetangga", callback_data="male_tetangga")],
            [InlineKeyboardButton("💔 Mantan", callback_data="male_mantan")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎭 **PILIH ROLE LAKI-LAKI**",
            reply_markup=reply_markup
        )
        return SELECTING_MALE_ROLE
    
    async def auto_story_male(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pilih role male dan durasi"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "⏱️ **MASUKKAN DURASI** (dalam jam)\n\nContoh: 2, 3, 6"
        )
        return INPUT_DURATION
    
    async def auto_story_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mulai auto story"""
        user_id = update.effective_user.id
        text = update.message.text
        
        try:
            duration = int(text.strip())
        except:
            await update.message.reply_text("❌ Masukkan angka yang valid")
            return INPUT_DURATION
        
        # Ambil role dari context
        female_role = context.user_data.get('female_role', 'ipar')
        male_role = context.user_data.get('male_role', 'suami')
        
        female_name, male_name = await self.auto_story.start_story(
            user_id, female_role, male_role, duration
        )
        
        await update.message.reply_text(
            f"🎬 **AUTO STORY DIMULAI**\n\n"
            f"👩 {female_name} ({female_role})\n"
            f"👨 {male_name} ({male_role})\n"
            f"⏱️ Durasi: {duration} jam\n\n"
            f"Gunakan /next untuk melanjutkan cerita"
        )
        
        return ACTIVE_SESSION
    
    async def next_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lanjutkan auto story"""
        user_id = update.effective_user.id
        
        female_msg, male_msg, success = await self.auto_story.generate_next(user_id)
        
        if success:
            await update.message.reply_text(f"👩 {female_msg}")
            await asyncio.sleep(1)
            await update.message.reply_text(f"👨 {male_msg}")
        else:
            await update.message.reply_text("❌ Gagal generate cerita")

# ===================== MAIN =====================

def main():
    bot = GadisUltimateV51()
    
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', bot.start_command)],
        states={
            SELECTING_MODE: [CallbackQueryHandler(bot.mode_callback)],
            SELECTING_FEMALE_ROLE: [CallbackQueryHandler(bot.auto_story_female, pattern='^role_')],
            SELECTING_MALE_ROLE: [CallbackQueryHandler(bot.auto_story_male, pattern='^male_')],
            INPUT_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.auto_story_start)],
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("status", bot.status_command))
    app.add_handler(CommandHandler("memory", bot.memory_command))
    app.add_handler(CommandHandler("dominant", bot.dominant_command))
    app.add_handler(CommandHandler("next", bot.next_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    print("\n" + "="*70)
    print("🚀 GADIS ULTIMATE V51.0 BERJALAN")
    print("="*70)
    print("\n🧠 Short-Term Memory: AKTIF")
    print("👑 Dominant Mode: SIAP")
    print("🤖 Auto Story: READY")
    print("\nTekan Ctrl+C untuk berhenti\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
