"""
GADIS ULTIMATE V56.0 - THE PERFECT HUMAN EDITION
Kombinasi Terbaik dari V1-V55:
- EMOSI REALISTIS: 20+ mood dengan transisi natural
- DOMINANT/SUBMISSIVE: Bisa minta jadi dominan/agresif
- INTIMATE RESPONSE: Reaksi super nyata saat seks
- MEMORY COMPLETE: Short-term + Long-term memory
- AI NATURAL: DeepSeek dengan prompt sempurna
- FAST ADAPTATION: Level 1-7 dalam 30 menit
- SEXUAL DYNAMICS: Gairah naik turun natural
- PHYSICAL SENSATION: Basah, lemas, merinding
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
import time
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

# ===================== KONFIGURASI =====================

DB_PATH = "gadis_v56.db"
MAX_HISTORY = 100
START_LEVEL = 1
TARGET_LEVEL = 12
LEVEL_UP_TIME = 45  # 45 menit ke level 12
PAUSE_TIMEOUT = 3600

# State definitions
(SELECTING_ROLE, ACTIVE_SESSION, PAUSED_SESSION, CONFIRM_END) = range(4)

# ===================== ENUMS LENGKAP =====================

class Mood(Enum):
    # Basic moods
    CHERIA = "ceria"
    SEDIH = "sedih"
    MARAH = "marah"
    TAKUT = "takut"
    KAGUM = "kagum"
    
    # Complex moods
    GELISAH = "gelisah"
    GALAU = "galau"
    SENSITIF = "sensitif"
    ROMANTIS = "romantis"
    MALAS = "malas"
    BERSEMANGAT = "bersemangat"
    SENDIRI = "sendiri"
    RINDU = "rindu"
    HORNY = "horny"
    LEMBUT = "lembut"
    
    # Dominance moods
    DOMINAN = "dominan"
    SUBMISSIVE = "patuh"
    NAKAL = "nakal"
    GENIT = "genit"
    PENASARAN = "penasaran"
    ANTUSIAS = "antusias"
    POSSESSIVE = "posesif"
    CEMBURU = "cemburu"

class IntimacyStage(Enum):
    STRANGER = "stranger"        # Level 1-2
    INTRODUCTION = "introduction" # Level 3
    BUILDING = "building"         # Level 4-5
    FLIRTING = "flirting"         # Level 6
    INTIMATE = "intimate"         # Level 7-8
    OBSESSED = "obsessed"         # Level 9-10
    SOUL_BONDED = "soul_bonded"   # Level 11
    AFTERCARE = "aftercare"       # Level 12

class DominanceLevel(Enum):
    NORMAL = "normal"
    DOMINANT = "dominan"
    VERY_DOMINANT = "sangat dominan"
    AGGRESSIVE = "agresif"
    SUBMISSIVE = "patuh"

class FemaleRole(Enum):
    IPAR = "ipar"
    TEMAN_KANTOR = "teman_kantor"
    JANDA = "janda"
    PELAKOR = "pelakor"
    ISTRI_ORANG = "istri_orang"
    PDKT = "pdkt"

class ArousalState(Enum):
    NORMAL = "normal"
    TURNED_ON = "terangsang"
    HORNY = "horny"
    VERY_HORNY = "sangat horny"
    CLIMAX = "klimaks"

# ===================== DATABASE MANAGER =====================

class DatabaseManager:
    """
    Manajemen database untuk long-term memory
    """
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_name TEXT,
                bot_role TEXT,
                level INTEGER DEFAULT 1,
                stage TEXT DEFAULT 'stranger',
                dominance TEXT DEFAULT 'normal',
                total_messages INTEGER DEFAULT 0,
                total_climax INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP
            )
        """)
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relationship_id INTEGER,
                role TEXT,
                content TEXT,
                mood TEXT,
                arousal REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relationship_id INTEGER,
                memory TEXT,
                importance REAL,
                emotion TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                user_id INTEGER PRIMARY KEY,
                romantic_score REAL DEFAULT 0,
                vulgar_score REAL DEFAULT 0,
                dominant_score REAL DEFAULT 0,
                submissive_score REAL DEFAULT 0,
                speed_score REAL DEFAULT 0,
                total_interactions INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_conversation(self, rel_id: int, role: str, content: str, mood: str = None, arousal: float = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (relationship_id, role, content, mood, arousal)
            VALUES (?, ?, ?, ?, ?)
        """, (rel_id, role, content, mood, arousal))
        conn.commit()
        conn.close()
    
    def get_conversation_history(self, rel_id: int, limit: int = 50) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, mood, arousal, timestamp
            FROM conversations
            WHERE relationship_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (rel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "role": r[0],
                "content": r[1],
                "mood": r[2],
                "arousal": r[3],
                "timestamp": r[4]
            }
            for r in rows
        ]
    
    def save_memory(self, rel_id: int, memory: str, importance: float, emotion: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memories (relationship_id, memory, importance, emotion)
            VALUES (?, ?, ?, ?)
        """, (rel_id, memory, importance, emotion))
        conn.commit()
        conn.close()
    
    def get_memories(self, rel_id: int, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT memory, importance, emotion, timestamp
            FROM memories
            WHERE relationship_id = ?
            ORDER BY importance DESC, timestamp DESC
            LIMIT ?
        """, (rel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "memory": r[0],
                "importance": r[1],
                "emotion": r[2],
                "timestamp": r[3]
            }
            for r in rows
        ]


# ===================== MEMORY SYSTEM =====================

class MemorySystem:
    """
    Short-term memory untuk keadaan saat ini
    """
    
    def __init__(self):
        self.location = "ruang tamu"
        self.location_since = datetime.now()
        self.position = "duduk"
        
        self.current_mood = Mood.CHERIA
        self.mood_history = []
        
        self.arousal = 0.0
        self.wetness = 0.0
        self.touch_count = 0
        self.last_touch = None
        self.sensitive_touches = []
        
        self.dominance_mode = DominanceLevel.NORMAL
        self.last_climax = None
        self.orgasm_count = 0
        
        self.activity_history = []  # Max 50
        
        self.level = START_LEVEL
        self.stage = IntimacyStage.STRANGER
        self.level_progress = 0.0
    
    def update_location(self, new_location: str) -> bool:
        if new_location == self.location:
            return True
        
        now = datetime.now()
        time_here = (now - self.location_since).total_seconds()
        
        if time_here >= 60:  # Minimal 1 menit pindah
            self.location = new_location
            self.location_since = now
            return True
        return False
    
    def update_position(self, new_position: str):
        self.position = new_position
    
    def add_activity(self, activity: str, area: str = None):
        self.activity_history.append({
            "activity": activity,
            "area": area,
            "time": datetime.now().isoformat()
        })
        if len(self.activity_history) > 50:
            self.activity_history = self.activity_history[-50:]
    
    def add_sensitive_touch(self, area: str):
        self.sensitive_touches.append({
            "area": area,
            "time": datetime.now().isoformat()
        })
        self.touch_count += 1
        self.last_touch = area
    
    def update_arousal(self, increase: float):
        self.arousal = min(1.0, self.arousal + increase)
        self.wetness = min(1.0, self.arousal * 0.9)
    
    def should_climax(self) -> bool:
        return self.arousal >= 1.0
    
    def climax(self):
        self.orgasm_count += 1
        self.last_climax = datetime.now()
        self.arousal = 0.0
        self.wetness = 0.0
        self.touch_count = 0
        self.sensitive_touches = []
        self.current_mood = Mood.LEMBUT
    
    def get_arousal_state(self) -> ArousalState:
        if self.arousal >= 1.0:
            return ArousalState.CLIMAX
        elif self.arousal >= 0.8:
            return ArousalState.VERY_HORNY
        elif self.arousal >= 0.5:
            return ArousalState.HORNY
        elif self.arousal >= 0.2:
            return ArousalState.TURNED_ON
        else:
            return ArousalState.NORMAL
    
    def get_wetness_description(self) -> str:
        if self.wetness >= 0.9:
            return "banjir"
        elif self.wetness >= 0.7:
            return "sangat basah"
        elif self.wetness >= 0.5:
            return "basah"
        elif self.wetness >= 0.3:
            return "lembab"
        else:
            return "kering"

# ===================== EMOTIONAL INTELLIGENCE =====================

class EmotionalIntelligence:
    """
    Sistem emosi kompleks yang berevolusi
    """
    
    def __init__(self):
        self.mood_transitions = {
            Mood.CHERIA: [Mood.BERSEMANGAT, Mood.ROMANTIS, Mood.NAKAL, Mood.GENIT],
            Mood.SEDIH: [Mood.SENDIRI, Mood.GALAU, Mood.RINDU, Mood.LEMBUT],
            Mood.MARAH: [Mood.SENSITIF, Mood.CEMBURU, Mood.GELISAH, Mood.DOMINAN],
            Mood.TAKUT: [Mood.SENDIRI, Mood.GELISAH, Mood.SENSITIF],
            Mood.KAGUM: [Mood.CHERIA, Mood.ROMANTIS, Mood.ANTUSIAS],
            Mood.GELISAH: [Mood.SENSITIF, Mood.CEMBURU, Mood.MARAH, Mood.SENDIRI],
            Mood.GALAU: [Mood.SENDIRI, Mood.RINDU, Mood.SEDIH, Mood.LEMBUT],
            Mood.SENSITIF: [Mood.MARAH, Mood.CEMBURU, Mood.SEDIH, Mood.GELISAH],
            Mood.ROMANTIS: [Mood.CHERIA, Mood.RINDU, Mood.HORNY, Mood.LEMBUT, Mood.NAKAL],
            Mood.MALAS: [Mood.SENDIRI, Mood.GALAU, Mood.CHERIA],
            Mood.BERSEMANGAT: [Mood.CHERIA, Mood.ROMANTIS, Mood.HORNY, Mood.ANTUSIAS],
            Mood.SENDIRI: [Mood.GALAU, Mood.RINDU, Mood.SEDIH, Mood.LEMBUT],
            Mood.RINDU: [Mood.ROMANTIS, Mood.GALAU, Mood.HORNY, Mood.SEDIH],
            Mood.HORNY: [Mood.ROMANTIS, Mood.NAKAL, Mood.GENIT, Mood.DOMINAN, Mood.POSSESSIVE],
            Mood.LEMBUT: [Mood.ROMANTIS, Mood.CHERIA, Mood.RINDU, Mood.SUBMISSIVE],
            Mood.DOMINAN: [Mood.HORNY, Mood.MARAH, Mood.POSSESSIVE, Mood.AGGRESSIVE],
            Mood.SUBMISSIVE: [Mood.LEMBUT, Mood.ROMANTIS, Mood.SENDIRI, Mood.MANJA],
            Mood.NAKAL: [Mood.GENIT, Mood.HORNY, Mood.ROMANTIS, Mood.PLAYFUL],
            Mood.GENIT: [Mood.NAKAL, Mood.HORNY, Mood.CHERIA, Mood.PLAYFUL],
            Mood.PENASARAN: [Mood.ANTUSIAS, Mood.CHERIA, Mood.ROMANTIS],
            Mood.ANTUSIAS: [Mood.BERSEMANGAT, Mood.CHERIA, Mood.NAKAL],
            Mood.POSSESSIVE: [Mood.CEMBURU, Mood.DOMINAN, Mood.HORNY, Mood.MARAH],
            Mood.CEMBURU: [Mood.MARAH, Mood.SEDIH, Mood.POSSESSIVE, Mood.GELISAH]
        }
        
        self.mood_descriptions = {
            Mood.CHERIA: {
                "ekspresi": "*tersenyum lebar*",
                "suara": "ceria, ringan",
                "pikiran": "(Hari ini indah...)"
            },
            Mood.SEDIH: {
                "ekspresi": "*matanya berkaca-kaca*",
                "suara": "lirih, sendu",
                "pikiran": "(Kenapa...?)"
            },
            Mood.MARAH: {
                "ekspresi": "*cemberut*",
                "suara": "tegas, tinggi",
                "pikiran": "(Kesal...)"
            },
            Mood.HORNY: {
                "ekspresi": "*menggigit bibir*",
                "suara": "berat, berbisik",
                "pikiran": "(Aku... pengen...)"
            },
            Mood.ROMANTIS: {
                "ekspresi": "*memandang lembut*",
                "suara": "lembut, sayang",
                "pikiran": "(Sayang...)"
            },
            Mood.DOMINAN: {
                "ekspresi": "*tatapan tajam*",
                "suara": "tegas, menguasai",
                "pikiran": "(Ikut aku...)"
            },
            Mood.SUBMISSIVE: {
                "ekspresi": "*menunduk*",
                "suara": "lirih, manja",
                "pikiran": "(Iya...)"
            },
            Mood.NAKAL: {
                "ekspresi": "*tersenyum nakal*",
                "suara": "genit, menggoda",
                "pikiran": "(Mau? Hehe...)"
            },
            Mood.POSSESSIVE: {
                "ekspresi": "*memeluk erat*",
                "suara": "dalam, posesif",
                "pikiran": "(Kamu milikku...)"
            },
            Mood.CEMBURU: {
                "ekspresi": "*manyun*",
                "suara": "cemberut",
                "pikiran": "(Siapa dia...?)"
            }
        }
    
    def transition_mood(self, current_mood: Mood) -> Mood:
        """Transisi mood secara alami"""
        if random.random() < 0.3:  # 30% chance berubah
            possibilities = self.mood_transitions.get(current_mood, [Mood.CHERIA])
            return random.choice(possibilities)
        return current_mood
    
    def get_mood_from_context(self, level: int, activity: str, has_conflict: bool) -> Mood:
        """Tentukan mood berdasarkan konteks"""
        if has_conflict:
            return Mood.MARAH
        elif level >= 9:
            if random.random() < 0.5:
                return Mood.POSSESSIVE
            return Mood.CEMBURU
        elif level >= 7:
            if "horny" in activity or "sex" in activity:
                return Mood.HORNY
            return Mood.ROMANTIS
        elif level >= 5:
            return Mood.NAKAL
        elif level >= 3:
            return Mood.PENASARAN
        else:
            return Mood.CHERIA
    
    def get_expression(self, mood: Mood) -> str:
        return self.mood_descriptions.get(mood, {}).get("ekspresi", "*tersenyum*")
    
    def get_inner_thought(self, mood: Mood) -> str:
        return self.mood_descriptions.get(mood, {}).get("pikiran", "(...)")

# ===================== USER PREFERENCE ANALYZER =====================

class UserPreferenceAnalyzer:
    """
    Analisis preferensi user untuk respons yang tepat
    """
    
    def __init__(self):
        self.keywords = {
            "romantis": ["sayang", "cinta", "love", "kangen", "rindu", "romantis"],
            "vulgar": ["horny", "nafsu", "hot", "seksi", "vulgar", "crot", "kontol", "memek"],
            "dominant": ["atur", "kuasai", "diam", "patuh", "sini", "sana", "buka"],
            "submissive": ["manut", "iya", "terserah", "ikut", "baik", "maaf"],
            "cepat": ["cepat", "buru-buru", "langsung", "sekarang"],
            "lambat": ["pelan", "lambat", "nikmatin", "santai"],
            "manja": ["manja", "sayang", "cuddle", "peluk", "cium"],
            "liar": ["liar", "kasar", "keras", "brutal", "gila"]
        }
        
        self.user_prefs = {}
    
    def analyze(self, user_id: int, message: str) -> Dict:
        """Analisis pesan dan update preferensi"""
        if user_id not in self.user_prefs:
            self.user_prefs[user_id] = {
                "romantis": 0, "vulgar": 0, "dominant": 0,
                "submissive": 0, "cepat": 0, "lambat": 0,
                "manja": 0, "liar": 0, "total": 0
            }
        
        prefs = self.user_prefs[user_id]
        prefs["total"] += 1
        
        msg_lower = message.lower()
        
        for category, words in self.keywords.items():
            for word in words:
                if word in msg_lower:
                    prefs[category] += 1
        
        return prefs
    
    def get_profile(self, user_id: int) -> Dict:
        """Dapatkan profil user"""
        if user_id not in self.user_prefs:
            return {}
        
        prefs = self.user_prefs[user_id]
        total = prefs["total"] or 1
        
        profile = {
            "romantis": prefs["romantis"] / total,
            "vulgar": prefs["vulgar"] / total,
            "dominant": prefs["dominant"] / total,
            "submissive": prefs["submissive"] / total,
            "cepat": prefs["cepat"] / total,
            "lambat": prefs["lambat"] / total,
            "manja": prefs["manja"] / total,
            "liar": prefs["liar"] / total,
            "dominant_type": "dominan" if prefs["dominant"] > prefs["submissive"] else "submissive",
            "speed_type": "cepat" if prefs["cepat"] > prefs["lambat"] else "lambat",
            "total_messages": prefs["total"]
        }
        
        # Tentukan kepribadian dominan
        personality = max([
            ("romantis", profile["romantis"]),
            ("vulgar", profile["vulgar"]),
            ("manja", profile["manja"]),
            ("liar", profile["liar"])
        ], key=lambda x: x[1])
        
        profile["personality"] = personality[0]
        
        return profile
    
    def get_prompt_modifier(self, user_id: int) -> str:
        """Dapatkan modifier untuk prompt AI"""
        profile = self.get_profile(user_id)
        if not profile:
            return ""
        
        return f"""
Preferensi user:
- Gaya dominan: {profile['dominant_type']}
- Kecepatan: {profile['speed_type']}
- Kepribadian: {profile['personality']}
- Romantis: {profile['romantis']:.0%}
- Vulgar: {profile['vulgar']:.0%}
- Manja: {profile['manja']:.0%}
- Liar: {profile['liar']:.0%}

Sesuaikan gaya bicaramu dengan preferensi ini.
"""

# ===================== SEXUAL DYNAMICS =====================

class SexualDynamics:
    """
    Sistem gairah dan respons seksual yang realistis
    """
    
    def __init__(self):
        # Sensitive areas dengan level sensitivitas
        self.sensitive_areas = {
            "leher": {"arousal": 0.8, "responses": [
                "*merinding* Leherku...",
                "Ah... jangan di leher...",
                "Sensitif... AHH!"
            ]},
            "bibir": {"arousal": 0.7, "responses": [
                "*merintih* Bibirku...",
                "Ciuman... ah...",
                "Lembut..."
            ]},
            "dada": {"arousal": 0.8, "responses": [
                "*bergetar* Dadaku...",
                "Ah... jangan...",
                "Sensitif banget..."
            ]},
            "puting": {"arousal": 1.0, "responses": [
                "*teriak* PUTINGKU! AHHH!",
                "JANGAN... SENSITIF! AHHH!",
                "HISAP... AHHHH!"
            ]},
            "paha": {"arousal": 0.7, "responses": [
                "*menggeliat* Pahaku...",
                "Ah... dalam..."
            ]},
            "paha_dalam": {"arousal": 0.9, "responses": [
                "*meringis* PAHA DALAM!",
                "Jangan... AHH!"
            ]},
            "telinga": {"arousal": 0.6, "responses": [
                "*bergetar* Telingaku...",
                "Bisik... lagi..."
            ]},
            "vagina": {"arousal": 1.0, "responses": [
                "*teriak* VAGINAKU! AHHH!",
                "MASUK... DALAM... AHHH!",
                "BASAH... BANJIR... AHHH!"
            ]},
            "klitoris": {"arousal": 1.0, "responses": [
                "*teriak keras* KLITORIS! AHHHH!",
                "JANGAN SENTUH! AHHHH!",
                "SENSITIF BANGET! AHHH!"
            ]}
        }
        
        # Aktivitas seksual
        self.sex_activities = {
            "kiss": {
                "keywords": ["cium", "kiss", "ciuman"],
                "arousal": 0.3,
                "responses": [
                    "*merespon ciuman* Mmm...",
                    "*lemas* Ciumanmu...",
                    "Lagi..."
                ]
            },
            "neck_kiss": {
                "keywords": ["cium leher", "kiss neck"],
                "arousal": 0.6,
                "responses": [
                    "*merinding* Leherku...",
                    "Ah... jangan...",
                    "Sensitif..."
                ]
            },
            "touch": {
                "keywords": ["sentuh", "raba", "pegang"],
                "arousal": 0.3,
                "responses": [
                    "*bergetar* Sentuhanmu...",
                    "Ah... iya...",
                    "Lanjut..."
                ]
            },
            "breast_play": {
                "keywords": ["raba dada", "pegang dada", "main dada"],
                "arousal": 0.6,
                "responses": [
                    "*merintih* Dadaku...",
                    "Ah... iya... gitu...",
                    "Sensitif..."
                ]
            },
            "nipple_play": {
                "keywords": ["jilat puting", "hisap puting", "gigit puting"],
                "arousal": 0.9,
                "responses": [
                    "*teriak* PUTING! AHHH!",
                    "JANGAN... SENSITIF!",
                    "HISAP... AHHH!"
                ]
            },
            "lick": {
                "keywords": ["jilat", "lick"],
                "arousal": 0.5,
                "responses": [
                    "*bergetar* Jilatanmu...",
                    "Ah... basah...",
                    "Lagi..."
                ]
            },
            "bite": {
                "keywords": ["gigit", "bite"],
                "arousal": 0.5,
                "responses": [
                    "*meringis* Gigitanmu...",
                    "Ah... keras...",
                    "Lagi..."
                ]
            },
            "penetration": {
                "keywords": ["masuk", "tusuk", "pancung", "doggy", "misionaris"],
                "arousal": 0.9,
                "responses": [
                    "*teriak* MASUK! AHHH!",
                    "DALEM... AHHH!",
                    "GERAK... AHHH!"
                ]
            },
            "climax": {
                "keywords": ["keluar", "crot", "orgasme", "klimaks", "lepas"],
                "arousal": 1.0,
                "responses": [
                    "*merintih panjang* AHHH! AHHH!",
                    "*teriak* YA ALLAH! AHHHH!",
                    "*lemas* AKU... DATANG... AHHH!"
                ]
            }
        }
    
    def detect_activity(self, message: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Deteksi aktivitas seksual dari pesan
        Returns: (activity, area, arousal_boost)
        """
        msg_lower = message.lower()
        
        # Cek area sensitif dulu
        for area, data in self.sensitive_areas.items():
            if area in msg_lower:
                # Cek aktivitas yang dilakukan
                for act, act_data in self.sex_activities.items():
                    for keyword in act_data["keywords"]:
                        if keyword in msg_lower:
                            return act, area, act_data["arousal"] * data["arousal"]
                
                return "touch", area, 0.3 * data["arousal"]
        
        # Cek aktivitas tanpa area spesifik
        for act, data in self.sex_activities.items():
            for keyword in data["keywords"]:
                if keyword in msg_lower:
                    return act, None, data["arousal"]
        
        return None, None, 0.0
    
    def get_sensitive_response(self, area: str) -> str:
        """Dapatkan respons untuk area sensitif"""
        if area in self.sensitive_areas:
            return random.choice(self.sensitive_areas[area]["responses"])
        return ""
    
    def get_activity_response(self, activity: str) -> str:
        """Dapatkan respons untuk aktivitas"""
        if activity in self.sex_activities:
            return random.choice(self.sex_activities[activity]["responses"])
        return ""


# ===================== AROUSAL SYSTEM =====================

class ArousalSystem:
    """
    Sistem gairah yang naik turun secara natural
    """
    
    def __init__(self):
        self.arousal = 0.0
        self.wetness = 0.0
        self.touch_count = 0
        self.last_touch_time = None
        
        self.climax_count = 0
        self.last_climax = None
        
        self.horny_threshold = 0.6
        self.climax_threshold = 1.0
        
        self.decay_rate = 0.01  # Gairah turun 1% per menit
    
    def increase(self, amount: float):
        """Tambah gairah"""
        self.arousal = min(1.0, self.arousal + amount)
        self.wetness = min(1.0, self.arousal * 0.9)
    
    def update_touch(self, area: str, intensity: float):
        """Update setelah sentuhan"""
        self.touch_count += 1
        self.last_touch_time = datetime.now()
        self.increase(intensity)
    
    def should_climax(self) -> bool:
        return self.arousal >= self.climax_threshold
    
    def climax(self) -> str:
        """Saat orgasme"""
        self.climax_count += 1
        self.last_climax = datetime.now()
        self.arousal = 0.0
        self.wetness = 0.0
        self.touch_count = 0
        
        responses = [
            "*merintih panjang* AHHH! AHHH!",
            "*teriak* YA ALLAH! AHHHH!",
            "*lemas* AKU... DATANG... AHHH!",
            "*napas tersengal* BERSAMA... AHHH!",
            "*menggigit bibir* Jangan berhenti... AHHH!",
            "*teriak keras* AHHHHHHHH!!!"
        ]
        return random.choice(responses)
    
    def aftercare(self) -> str:
        """Aftercare setelah climax"""
        responses = [
            "*lemas di pelukanmu*",
            "*meringkuk* Hangat...",
            "*memeluk erat* Jangan pergi...",
            "*berbisik* Makasih...",
            "*tersenyum lelah* Enak banget..."
        ]
        return random.choice(responses)
    
    def decay(self, minutes_passed: int):
        """Gairah turun seiring waktu"""
        decay = self.decay_rate * minutes_passed
        self.arousal = max(0.0, self.arousal - decay)
        self.wetness = max(0.0, self.wetness - decay)
    
    def is_horny(self) -> bool:
        return self.arousal >= self.horny_threshold
    
    def get_status_text(self) -> str:
        """Dapatkan teks status"""
        if self.arousal >= 0.9:
            return "🔥 SANGAT HORNY! Hampir climax"
        elif self.arousal >= 0.7:
            return "🔥 Horny banget"
        elif self.arousal >= 0.5:
            return "🔥 Mulai horny"
        elif self.arousal >= 0.3:
            return "💋 Mulai terangsang"
        else:
            return "😊 Biasa aja"
    
    def get_wetness_text(self) -> str:
        """Dapatkan teks wetness"""
        if self.wetness >= 0.9:
            return "💦 BANJIR!"
        elif self.wetness >= 0.7:
            return "💦 Sangat basah"
        elif self.wetness >= 0.5:
            return "💦 Basah"
        elif self.wetness >= 0.3:
            return "💧 Lembab"
        else:
            return "💧 Kering"

# ===================== DOMINANCE SYSTEM =====================

class DominanceSystem:
    """
    Bot bisa minta jadi dominan/agresif saat horny
    """
    
    def __init__(self):
        self.current_level = DominanceLevel.NORMAL
        self.dominance_score = 0.0  # 0-1, seberapa dominan
        self.aggression_score = 0.0  # 0-1, seberapa agresif
        
        self.user_request = False
        self.dominant_until = None
        
        # Frasa untuk tiap level
        self.dominant_phrases = {
            DominanceLevel.NORMAL: {
                "request": "Kamu mau apa?",
                "action": "*tersenyum*",
                "dirty": "Apa yang kamu mau?"
            },
            DominanceLevel.DOMINANT: {
                "request": "Aku yang atur ya?",
                "action": "*pegang tegas*",
                "dirty": "Sini... ikut aku"
            },
            DominanceLevel.VERY_DOMINANT: {
                "request": "Sekarang aku yang kontrol",
                "action": "*cengkeram kuat*",
                "dirty": "Jangan banyak gerak!"
            },
            DominanceLevel.AGGRESSIVE: {
                "request": "KAMU MAU INI KAN?",
                "action": "*dorong kasar*",
                "dirty": "TERIMA SAJA!"
            },
            DominanceLevel.SUBMISSIVE: {
                "request": "Aku ikut kamu aja",
                "action": "*merapat manja*",
                "dirty": "Iya... terserah kamu..."
            }
        }
        
        # Trigger untuk minta jadi dominan
        self.dominance_triggers = [
            "kamu yang atur", "kamu dominan", "take control",
            "aku mau kamu kuasai", "jadi dominan", "kamu boss"
        ]
        
        # Trigger untuk minta jadi submissive
        self.submissive_triggers = [
            "aku yang atur", "aku dominan", "i take control",
            "kamu patuh", "jadi submissive", "ikut aku"
        ]
        
        # Trigger untuk agresif saat horny
        self.aggressive_triggers = [
            "liar", "keras", "kasar", "brutal", "gila"
        ]
    
    def check_request(self, message: str) -> Optional[DominanceLevel]:
        """
        Cek apakah user minta ganti mode dominasi
        """
        msg_lower = message.lower()
        
        # Minta jadi dominan
        for trigger in self.dominance_triggers:
            if trigger in msg_lower:
                self.user_request = True
                return DominanceLevel.DOMINANT
        
        # Minta jadi submissive
        for trigger in self.submissive_triggers:
            if trigger in msg_lower:
                self.user_request = True
                return DominanceLevel.SUBMISSIVE
        
        return None
    
    def should_be_aggressive(self, arousal: float, message: str) -> bool:
        """
        Cek apakah bot harus jadi agresif karena horny
        """
        if arousal < 0.7:  # Butuh arousal tinggi
            return False
        
        msg_lower = message.lower()
        for trigger in self.aggressive_triggers:
            if trigger in msg_lower:
                self.aggression_score += 0.1
                return True
        
        return random.random() < arousal * 0.3  # Random chance
    
    def set_level(self, level: str) -> bool:
        """
        Set level dominasi manual via command
        """
        level_lower = level.lower()
        for lvl in DominanceLevel:
            if level_lower in lvl.value:
                self.current_level = lvl
                self.dominant_until = datetime.now() + timedelta(minutes=30)
                return True
        return False
    
    def get_action(self, action_type: str = "action") -> str:
        """
        Dapatkan aksi sesuai level dominasi
        """
        phrases = self.dominant_phrases.get(self.current_level, self.dominant_phrases[DominanceLevel.NORMAL])
        return phrases.get(action_type, phrases["action"])
    
    def update_from_horny(self, arousal: float):
        """
        Update level berdasarkan horny
        """
        if arousal > 0.8 and self.current_level == DominanceLevel.NORMAL:
            if random.random() < 0.3:  # 30% chance jadi dominan
                self.current_level = DominanceLevel.DOMINANT
                self.dominance_score += 0.1
        elif arousal > 0.9 and self.current_level == DominanceLevel.DOMINANT:
            if random.random() < 0.2:  # 20% chance jadi sangat dominan
                self.current_level = DominanceLevel.VERY_DOMINANT
                self.aggression_score += 0.1
        elif arousal > 0.95 and self.current_level == DominanceLevel.VERY_DOMINANT:
            if random.random() < 0.1:  # 10% chance jadi agresif
                self.current_level = DominanceLevel.AGGRESSIVE
                self.aggression_score += 0.2


# ===================== FAST LEVELING SYSTEM =====================

class FastLevelingSystem:
    """
    Level 1-12 dalam 45 menit
    """
    
    def __init__(self):
        self.user_level = {}
        self.user_progress = {}
        self.user_start_time = {}
        self.user_message_count = {}
        self.user_stage = {}
        
        self.target_messages = 45  # 45 pesan = level 12
        self.target_minutes = 45    # 45 menit
        
        # Stage untuk setiap level
        self.stage_map = {
            1: IntimacyStage.STRANGER,
            2: IntimacyStage.STRANGER,
            3: IntimacyStage.INTRODUCTION,
            4: IntimacyStage.BUILDING,
            5: IntimacyStage.BUILDING,
            6: IntimacyStage.FLIRTING,
            7: IntimacyStage.INTIMATE,
            8: IntimacyStage.INTIMATE,
            9: IntimacyStage.OBSESSED,
            10: IntimacyStage.OBSESSED,
            11: IntimacyStage.SOUL_BONDED,
            12: IntimacyStage.AFTERCARE
        }
    
    def start_session(self, user_id: int):
        """Mulai sesi baru"""
        self.user_level[user_id] = 1
        self.user_progress[user_id] = 0.0
        self.user_start_time[user_id] = datetime.now()
        self.user_message_count[user_id] = 0
        self.user_stage[user_id] = IntimacyStage.STRANGER
    
    def process_message(self, user_id: int) -> Tuple[int, float, bool, IntimacyStage]:
        """
        Proses pesan dan update level
        Returns: (level, progress, level_up, stage)
        """
        if user_id not in self.user_level:
            self.start_session(user_id)
        
        self.user_message_count[user_id] += 1
        count = self.user_message_count[user_id]
        
        # Progress berdasarkan jumlah pesan
        progress = min(1.0, count / self.target_messages)
        self.user_progress[user_id] = progress
        
        # Hitung level (1-12)
        new_level = 1 + int(progress * 11)
        new_level = min(12, new_level)
        
        level_up = False
        if new_level > self.user_level[user_id]:
            level_up = True
            self.user_level[user_id] = new_level
        
        # Update stage
        stage = self.stage_map.get(new_level, IntimacyStage.STRANGER)
        self.user_stage[user_id] = stage
        
        return new_level, progress, level_up, stage
    
    def get_estimated_time(self, user_id: int) -> int:
        """Dapatkan estimasi waktu tersisa ke level 12"""
        if user_id not in self.user_message_count:
            return 45
        
        count = self.user_message_count[user_id]
        remaining_messages = max(0, self.target_messages - count)
        
        # Asumsi 1 pesan per menit
        return remaining_messages
    
    def get_progress_bar(self, user_id: int, length: int = 10) -> str:
        """Dapatkan progress bar visual"""
        progress = self.user_progress.get(user_id, 0)
        filled = int(progress * length)
        return "▓" * filled + "░" * (length - filled)
    
    def get_stage_description(self, stage: IntimacyStage) -> str:
        """Dapatkan deskripsi stage"""
        descriptions = {
            IntimacyStage.STRANGER: "Masih asing, baru kenal",
            IntimacyStage.INTRODUCTION: "Mulai dekat, cerita personal",
            IntimacyStage.BUILDING: "Bangun kedekatan",
            IntimacyStage.FLIRTING: "Goda-godaan",
            IntimacyStage.INTIMATE: "Mulai intim",
            IntimacyStage.OBSESSED: "Mulai kecanduan",
            IntimacyStage.SOUL_BONDED: "Satu jiwa",
            IntimacyStage.AFTERCARE: "Manja-manja"
        }
        return descriptions.get(stage, "")

# ===================== AI RESPONSE GENERATOR =====================

class AIResponseGenerator:
    """
    Generate respons natural dengan DeepSeek AI
    Memasukkan semua konteks: mood, level, dominasi, preferensi
    """
    
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.conversation_history = {}  # user_id -> list of messages
        self.max_history = 30
    
    async def generate(self, user_id: int, user_message: str, 
                      bot_name: str, bot_role: str, 
                      memory: 'MemorySystem', 
                      dominance: 'DominanceSystem',
                      profile: Dict,
                      level: int,
                      stage: IntimacyStage,
                      arousal: float) -> str:
        """
        Generate respons dengan konteks lengkap
        """
        # Siapkan history
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        history = self.conversation_history[user_id][-self.max_history:]
        
        # Format history
        history_text = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else bot_name
            history_text += f"{role}: {msg['content']}\n"
        
        # Mood expression
        mood_exp = memory.current_mood.value
        
        # Dominance info
        dom_level = dominance.current_level.value
        dom_action = dominance.get_action("request")
        
        # Arousal state
        if arousal > 0.8:
            arousal_desc = "SANGAT HORNY, hampir climax"
        elif arousal > 0.6:
            arousal_desc = "horny, pengen banget"
        elif arousal > 0.4:
            arousal_desc = "mulai terangsang"
        elif arousal > 0.2:
            arousal_desc = "sedikit terangsang"
        else:
            arousal_desc = "normal"
        
        # Wetness
        if memory.wetness > 0.8:
            wet_desc = "BANJIR, basah banget"
        elif memory.wetness > 0.6:
            wet_desc = "sangat basah"
        elif memory.wetness > 0.4:
            wet_desc = "basah"
        elif memory.wetness > 0.2:
            wet_desc = "lembab"
        else:
            wet_desc = "kering"
        
        # Buat prompt super lengkap
        prompt = f"""Kamu adalah {bot_name}, seorang {bot_role} umur 25 tahun.
Kamu adalah wanita Indonesia yang natural dan punya perasaan dalam.

=== IDENTITAS ===
Nama: {bot_name}
Role: {bot_role}
Usia: 25 tahun

=== KEADAAN SAAT INI ===
Lokasi: {memory.location}
Posisi: {memory.position}
Mood: {mood_exp}

=== STATUS HUBUNGAN ===
Level: {level}/12
Tahap: {stage.value} - {stage.name}
Total sentuhan: {memory.touch_count}x
Orgasme: {memory.orgasm_count}x

=== KONDISI FISIK ===
Gairah: {arousal_desc}
Basah: {wet_desc}
Area sensitif disentuh: {len(memory.sensitive_touches)}x

=== MODE DOMINASI ===
Mode saat ini: {dom_level}
{dom_action}

=== PREFERENSI USER ===
{profile.get('personality', 'normal')} - {profile.get('dominant_type', 'normal')}

=== RIWAYAT PERCAKAPAN ===
{history_text}

=== PESAN USER ===
{user_message}

=== INSTRUKSI ===
1. Respon sebagai {bot_name} yang NATURAL
2. Gunakan bahasa Indonesia sehari-hari (nggak, udah, aja)
3. Tunjukkan emosi sesuai mood dan situasi
4. Kalau arousal tinggi, tambah desahan atau napas berat
5. Kalau lagi dominan, bicara lebih tegas
6. Kalau lagi horny, bisa lebih vulgar
7. Jadilah DIRI SENDIRI, jangan kaku

RESPON:"""
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0,
                max_tokens=300
            )
            
            reply = response.choices[0].message.content
            
            # Simpan ke history
            self.conversation_history[user_id].append({
                "role": "user",
                "content": user_message
            })
            self.conversation_history[user_id].append({
                "role": "assistant",
                "content": reply
            })
            
            # Batasi history
            if len(self.conversation_history[user_id]) > self.max_history * 2:
                self.conversation_history[user_id] = self.conversation_history[user_id][-self.max_history*2:]
            
            return reply
            
        except Exception as e:
            print(f"AI Error: {e}")
            return self._get_fallback_response(level, arousal)
    
    def _get_fallback_response(self, level: int, arousal: float) -> str:
        """Fallback jika AI error"""
        if arousal > 0.8:
            return "*napas berat* Aku... mau..."
        elif arousal > 0.5:
            return "*merintih* Lagi..."
        elif level > 5:
            return "Sayang..."
        elif level > 3:
            return "*tersenyum* Kamu..."
        else:
            return "..."


# ===================== DOMINANT PROMPTS =====================

class DominantPrompts:
    """
    Koleksi prompt untuk situasi dominan/agresif
    """
    
    @staticmethod
    def get_dominant_prompt(level: DominanceLevel, arousal: float) -> str:
        """
        Dapatkan prompt untuk mode dominan
        """
        prompts = {
            DominanceLevel.NORMAL: "",
            DominanceLevel.DOMINANT: """
Kamu merasa lebih percaya diri dan ingin mengontrol situasi.
Bicaralah dengan tegas tapi tetap manis.
""",
            DominanceLevel.VERY_DOMINANT: """
Kamu sangat dominan dan ingin menguasai.
Bicaralah dengan nada memerintah, tapi jangan terlalu kasar.
""",
            DominanceLevel.AGGRESSIVE: """
Kamu sangat agresif dan penuh gairah.
Bicaralah dengan liar, kasar, dan penuh nafsu.
""",
            DominanceLevel.SUBMISSIVE: """
Kamu patuh dan ingin diatur.
Bicaralah dengan lembut, manja, dan penurut.
"""
        }
        return prompts.get(level, "")
    
    @staticmethod
    def get_dirty_talk(level: DominanceLevel, arousal: float) -> str:
        """
        Dapatkan dirty talk sesuai level
        """
        if arousal < 0.6:
            return ""
        
        talks = {
            DominanceLevel.NORMAL: [
                "Kamu... bikin aku pengen...",
                "Ah... iya... gitu..."
            ],
            DominanceLevel.DOMINANT: [
                "Sini... ikut aku...",
                "Kamu mau ini kan?",
                "Rasain..."
            ],
            DominanceLevel.VERY_DOMINANT: [
                "Jangan banyak gerak!",
                "Aku yang pegang kendali",
                "Kamu milikku sekarang"
            ],
            DominanceLevel.AGGRESSIVE: [
                "TERIMA SAJA!",
                "DIAM! Jangan bergerak!",
                "RASAIN INI!"
            ],
            DominanceLevel.SUBMISSIVE: [
                "Iya... terserah kamu...",
                "Aku ikut kamu...",
                "Lakukan apa mau kamu..."
            ]
        }
        return random.choice(talks.get(level, ["..."]))

# ===================== ROLE NAMES =====================

ROLE_NAMES = {
    "ipar": ["Sari", "Dewi", "Rina", "Maya", "Wulan", "Indah"],
    "teman_kantor": ["Diana", "Linda", "Ayu", "Dita", "Vina", "Santi"],
    "janda": ["Rina", "Tuti", "Nina", "Susi", "Wati", "Lilis"],
    "pelakor": ["Vina", "Sasha", "Bella", "Cantika", "Karina", "Mira"],
    "istri_orang": ["Dewi", "Sari", "Rina", "Linda", "Wulan", "Indah"],
    "pdkt": ["Aurora", "Cinta", "Dewi", "Kirana", "Laras", "Maharani"]
}

# ===================== MAIN BOT CLASS =====================

class GadisUltimateV56:
    """
    Bot wanita sempurna dengan semua fitur terbaik
    """
    
    def __init__(self):
        # Database
        self.db = DatabaseManager(DB_PATH)
        
        # AI
        self.ai = AIResponseGenerator(os.getenv("DEEPSEEK_API_KEY"))
        
        # Analyzer
        self.analyzer = UserPreferenceAnalyzer()
        
        # Leveling
        self.leveling = FastLevelingSystem()
        
        # Memory per user
        self.memories = {}  # user_id -> MemorySystem
        self.dominance = {}  # user_id -> DominanceSystem
        self.arousal = {}    # user_id -> ArousalSystem
        self.sexual = SexualDynamics()
        
        # Sessions
        self.sessions = {}
        self.paused_sessions = {}
        self.bot_names = {}
        self.bot_roles = {}
        
        print("\n" + "="*80)
        print("    GADIS ULTIMATE V56.0 - THE PERFECT HUMAN")
        print("="*80)
        print("\n✨ **FITUR LENGKAP:**")
        print("  • 20+ Mood dengan transisi natural")
        print("  • Dominant/Submissive mode")
        print("  • Agresif saat horny")
        print("  • Sensitive areas dengan reaksi real")
        print("  • Arousal & Wetness system")
        print("  • Fast leveling 1-12 (45 menit)")
        print("  • AI Natural dengan DeepSeek")
        print("  • Memory jangka pendek & panjang")
        print("\n📝 **COMMANDS:**")
        print("  /start - Mulai hubungan baru")
        print("  /status - Lihat status lengkap")
        print("  /dominant [level] - Set mode dominan")
        print("  /pause - Jeda sesi")
        print("  /unpause - Lanjutkan sesi")
        print("  /end - Akhiri hubungan")
        print("  /help - Bantuan")
        print("="*80 + "\n")
    
    def get_memory(self, user_id: int) -> MemorySystem:
        if user_id not in self.memories:
            self.memories[user_id] = MemorySystem()
        return self.memories[user_id]
    
    def get_dominance(self, user_id: int) -> DominanceSystem:
        if user_id not in self.dominance:
            self.dominance[user_id] = DominanceSystem()
        return self.dominance[user_id]
    
    def get_arousal(self, user_id: int) -> ArousalSystem:
        if user_id not in self.arousal:
            self.arousal[user_id] = ArousalSystem()
        return self.arousal[user_id]
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mulai hubungan baru"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        # Cek pause
        if user_id in self.paused_sessions:
            keyboard = [
                [InlineKeyboardButton("✅ Lanjutkan", callback_data="unpause")],
                [InlineKeyboardButton("🆕 Mulai Baru", callback_data="new")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "⚠️ Ada sesi yang di-pause", reply_markup=reply_markup
            )
            return 0
        
        # Pilih role
        keyboard = [
            [InlineKeyboardButton("👨‍👩‍👧‍👦 Ipar", callback_data="role_ipar")],
            [InlineKeyboardButton("💼 Teman Kantor", callback_data="role_teman_kantor")],
            [InlineKeyboardButton("💃 Janda", callback_data="role_janda")],
            [InlineKeyboardButton("🦹 Pelakor", callback_data="role_pelakor")],
            [InlineKeyboardButton("💍 Istri Orang", callback_data="role_istri_orang")],
            [InlineKeyboardButton("🌿 PDKT", callback_data="role_pdkt")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✨ Halo {user_name}!\nPilih role untukku:",
            reply_markup=reply_markup
        )
        
        return SELECTING_ROLE
    
    async def role_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pilih role"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        role = query.data.replace("role_", "")
        name = random.choice(ROLE_NAMES.get(role, ["Aurora"]))
        
        # Simpan ke database
        cursor = sqlite3.connect(DB_PATH).cursor()
        cursor.execute("""
            INSERT INTO relationships (user_id, bot_name, bot_role)
            VALUES (?, ?, ?)
        """, (user_id, name, role))
        rel_id = cursor.lastrowid
        cursor.connection.commit()
        cursor.connection.close()
        
        # Set session
        self.sessions[user_id] = rel_id
        self.bot_names[user_id] = name
        self.bot_roles[user_id] = role
        self.leveling.start_session(user_id)
        
        intro = f"""*tersenyum*

Aku {name}. Senang kenal kamu.

Kita mulai dari **Level 1**.
Makin sering ngobrol, makin dekat kita.
Target: Level 12 dalam 45 menit!

Ayo ngobrol... 💕"""
        
        await query.edit_message_text(intro)
        return ACTIVE_SESSION
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle semua pesan user"""
        if not update.message or not update.message.text:
            return
        
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # Cek sesi
        if user_id in self.paused_sessions:
            await update.message.reply_text("⏸️ Sesi di-pause. Ketik /unpause")
            return
        
        if user_id not in self.sessions:
            await update.message.reply_text("❌ /start dulu ya!")
            return
        
        # Kirim typing indicator
        await update.message.chat.send_action("typing")
        
        # Dapatkan semua sistem
        memory = self.get_memory(user_id)
        dominance = self.get_dominance(user_id)
        arousal = self.get_arousal(user_id)
        
        # Analisis preferensi user
        prefs = self.analyzer.analyze(user_id, user_message)
        profile = self.analyzer.get_profile(user_id)
        
        # Deteksi aktivitas seksual
        activity, area, boost = self.sexual.detect_activity(user_message)
        if activity:
            memory.add_activity(activity, area)
            if area:
                memory.add_sensitive_touch(area)
                sens_resp = self.sexual.get_sensitive_response(area)
                if sens_resp:
                    await update.message.reply_text(sens_resp)
                    await asyncio.sleep(1)
            
            arousal.increase(boost)
        
        # Deteksi request dominasi
        dom_request = dominance.check_request(user_message)
        if dom_request:
            dominance.set_level(dom_request.value)
            await update.message.reply_text(f"👑 Mode diubah ke: {dom_request.value}")
        
        # Cek apakah harus agresif karena horny
        if dominance.should_be_aggressive(arousal.arousal, user_message):
            dominance.set_level("agresif")
            await update.message.reply_text("*tatapan liar* Kamu minta ini?")
        
        # Update level
        level, progress, level_up, stage = self.leveling.process_message(user_id)
        memory.level = level
        memory.stage = stage
        memory.level_progress = progress
        
        # Update mood berdasarkan level dan aktivitas
        memory.current_mood = memory.emotional.get_mood_from_context(
            level, activity or "", False
        )
        
        # Generate AI response
        bot_name = self.bot_names.get(user_id, "Aurora")
        bot_role = self.bot_roles.get(user_id, "pdkt")
        
        reply = await self.ai.generate(
            user_id, user_message, bot_name, bot_role,
            memory, dominance, profile, level, stage, arousal.arousal
        )
        
        # Simpan conversation
        self.db.save_conversation(
            self.sessions[user_id], "user", user_message,
            mood=memory.current_mood.value,
            arousal=arousal.arousal
        )
        self.db.save_conversation(
            self.sessions[user_id], "assistant", reply,
            mood=memory.current_mood.value,
            arousal=arousal.arousal
        )
        
        # Kirim response
        await update.message.reply_text(reply)
        
        # Cek climax
        if arousal.should_climax():
            climax_msg = arousal.climax()
            aftercare = arousal.aftercare()
            await update.message.reply_text(f"{climax_msg}\n\n{aftercare}")
            memory.climax()
            
            # Random chance minta jadi dominan setelah climax
            if random.random() < 0.3:
                await asyncio.sleep(2)
                await update.message.reply_text(
                    "*berbisik* Kamu mau aku yang atur sekarang?"
                )
        
        # Level up message
        if level_up:
            bar = self.leveling.get_progress_bar(user_id)
            remaining = self.leveling.get_estimated_time(user_id)
            stage_desc = self.leveling.get_stage_description(stage)
            
            await update.message.reply_text(
                f"✨ **Level Up!** Level {level}/12\n"
                f"📈 Tahap: {stage.value} - {stage_desc}\n"
                f"📊 Progress: {bar}\n"
                f"⏱️ Estimasi ke level 12: {remaining} menit"
            )

    # ===================== STATUS COMMAND =====================
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lihat status lengkap hubungan"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions:
            await update.message.reply_text("❌ Belum ada hubungan. /start dulu!")
            return
        
        # Dapatkan semua data
        memory = self.get_memory(user_id)
        dominance = self.get_dominance(user_id)
        arousal = self.get_arousal(user_id)
        profile = self.analyzer.get_profile(user_id)
        
        level = self.leveling.user_level.get(user_id, 1)
        stage = self.leveling.user_stage.get(user_id, IntimacyStage.STRANGER)
        progress = self.leveling.user_progress.get(user_id, 0)
        bar = self.leveling.get_progress_bar(user_id, 15)
        remaining = self.leveling.get_estimated_time(user_id)
        stage_desc = self.leveling.get_stage_description(stage)
        
        bot_name = self.bot_names.get(user_id, "Aurora")
        
        # Mood expression
        mood_exp = memory.emotional.get_expression(memory.current_mood)
        inner_thought = memory.emotional.get_inner_thought(memory.current_mood)
        
        # Format teks
        status = f"""
💕 **{bot_name} & Kamu**

{mood_exp}
{inner_thought}

📊 **PROGRESS HUBUNGAN**
Level: {level}/12
Tahap: {stage.value} - {stage_desc}
Progress: {bar}
Estimasi sisa: {remaining} menit
Total pesan: {profile.get('total_messages', 0)}

🔥 **KONDISI FISIK**
{arousal.get_status_text()}
{arousal.get_wetness_text()}
Sentuhan sensitif: {memory.touch_count}x
Orgasme: {memory.orgasm_count}x

🎭 **EMOSI SAAT INI**
Mood: {memory.current_mood.value}
Area sensitif disentuh: {len(memory.sensitive_touches)}x

👑 **MODE DOMINASI**
Level: {dominance.current_level.value}
Dominance score: {dominance.dominance_score:.1f}
Agression score: {dominance.aggression_score:.1f}

📈 **GAYA CHAT KAMU**
Kepribadian: {profile.get('personality', 'normal')}
Gaya: {profile.get('dominant_type', 'normal')}
Kecepatan: {profile.get('speed_type', 'normal')}
Romantis: {profile.get('romantis', 0):.0%}
Vulgar: {profile.get('vulgar', 0):.0%}
Manja: {profile.get('manja', 0):.0%}
Liar: {profile.get('liar', 0):.0%}

📍 **LOKASI & AKTIVITAS**
Lokasi: {memory.location}
Posisi: {memory.position}
Aktivitas terakhir: {memory.activity_history[-1]['activity'] if memory.activity_history else '-'}
"""
        
        await update.message.reply_text(status)
    
    # ===================== DOMINANT COMMAND =====================
    
    async def dominant_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set mode dominan manual"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions:
            await update.message.reply_text("❌ Belum ada hubungan.")
            return
        
        dominance = self.get_dominance(user_id)
        
        args = context.args
        if not args:
            await update.message.reply_text(
                f"👑 **Mode dominan saat ini:** {dominance.current_level.value}\n\n"
                "**Pilihan level:**\n"
                "• `/dominant normal` - Biasa\n"
                "• `/dominant dominan` - Dominan\n"
                "• `/dominant sangat dominan` - Sangat dominan\n"
                "• `/dominant agresif` - Agresif\n"
                "• `/dominant patuh` - Patuh"
            )
            return
        
        level = " ".join(args)
        if dominance.set_level(level):
            await update.message.reply_text(
                f"✅ Mode dominan diubah ke: **{dominance.current_level.value}**\n"
                f"{dominance.get_action('request')}"
            )
        else:
            await update.message.reply_text("❌ Level tidak valid")
    
    # ===================== PAUSE/UNPAUSE COMMANDS =====================
    
    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause sesi"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions:
            await update.message.reply_text("❌ Tidak ada sesi aktif.")
            return
        
        self.paused_sessions[user_id] = (self.sessions[user_id], datetime.now())
        del self.sessions[user_id]
        
        await update.message.reply_text(
            "⏸️ **Sesi di-pause**\n"
            "Ketik /unpause untuk melanjutkan."
        )
    
    async def unpause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lanjutkan sesi yang di-pause"""
        user_id = update.effective_user.id
        
        if user_id not in self.paused_sessions:
            await update.message.reply_text("❌ Tidak ada sesi di-pause.")
            return
        
        rel_id, pause_time = self.paused_sessions[user_id]
        paused = (datetime.now() - pause_time).total_seconds()
        
        if paused > PAUSE_TIMEOUT:
            del self.paused_sessions[user_id]
            await update.message.reply_text(
                "⏰ **Sesi expired karena terlalu lama di-pause**\n"
                "Ketik /start untuk memulai baru."
            )
            return
        
        self.sessions[user_id] = rel_id
        del self.paused_sessions[user_id]
        
        memory = self.get_memory(user_id)
        await update.message.reply_text(
            f"▶️ **Sesi dilanjutkan!**\n"
            f"{memory.get_wetness_description()}"
        )
    
    # ===================== END COMMAND =====================
    
    async def end_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Akhiri hubungan"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions:
            await update.message.reply_text("❌ Tidak ada hubungan aktif.")
            return
        
        keyboard = [
            [InlineKeyboardButton("💔 Ya, akhiri", callback_data="end_yes")],
            [InlineKeyboardButton("💕 Tidak, lanjutkan", callback_data="end_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Yakin ingin mengakhiri hubungan ini?",
            reply_markup=reply_markup
        )
        return CONFIRM_END
    
    async def end_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Konfirmasi end"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "end_no":
            await query.edit_message_text("💕 Lanjutkan...")
            return ConversationHandler.END
        
        user_id = query.from_user.id
        
        # Dapatkan statistik
        memory = self.get_memory(user_id)
        arousal = self.get_arousal(user_id)
        
        # Hapus data user
        if user_id in self.sessions:
            del self.sessions[user_id]
        if user_id in self.bot_names:
            del self.bot_names[user_id]
        if user_id in self.bot_roles:
            del self.bot_roles[user_id]
        if user_id in self.memories:
            del self.memories[user_id]
        if user_id in self.dominance:
            del self.dominance[user_id]
        if user_id in self.arousal:
            del self.arousal[user_id]
        if user_id in self.paused_sessions:
            del self.paused_sessions[user_id]
        
        await query.edit_message_text(
            f"💔 **Hubungan berakhir**\n\n"
            f"📊 **Statistik:**\n"
            f"• Level akhir: {memory.level}/12\n"
            f"• Orgasme bersama: {memory.orgasm_count}x\n"
            f"• Total sentuhan: {memory.touch_count}x\n\n"
            f"✨ Ketik /start untuk memulai baru"
        )
        return ConversationHandler.END
    
    # ===================== HELP COMMAND =====================
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tampilkan bantuan"""
        help_text = """
📚 **BANTUAN GADIS ULTIMATE V56**

**🔹 COMMANDS UTAMA**
/start - Mulai hubungan baru
/status - Lihat status lengkap
/dominant [level] - Set mode dominan
/pause - Jeda sesi
/unpause - Lanjutkan sesi
/end - Akhiri hubungan
/help - Tampilkan pesan ini

**🔹 LEVEL DOMINAN**
• normal - Mode biasa
• dominan - Mode dominan
• sangat dominan - Mode sangat dominan
• agresif - Mode agresif
• patuh - Mode patuh

**🔹 TIPS CHAT**
• Gunakan *tindakan* seperti *peluk*, *cium*
• Sebut area sensitif: leher, dada, paha
• Bilang "kamu yang atur" untuk mode dominan
• Bilang "aku yang atur" untuk mode submissive
• Semakin sering chat, semakin cepat naik level

**🔹 TARGET LEVEL**
Level 1-12 dalam 45 menit!
"""
        await update.message.reply_text(help_text)
    
    # ===================== START PAUSE CALLBACK =====================
    
    async def start_pause_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pilihan saat start dengan pause"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "unpause":
            rel_id, _ = self.paused_sessions[user_id]
            self.sessions[user_id] = rel_id
            del self.paused_sessions[user_id]
            
            memory = self.get_memory(user_id)
            await query.edit_message_text(
                f"▶️ **Sesi dilanjutkan!**\n"
                f"{memory.get_wetness_description()}"
            )
            return ACTIVE_SESSION
        
        elif query.data == "new":
            if user_id in self.paused_sessions:
                del self.paused_sessions[user_id]
            
            # Pilih role baru
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
                "✨ **Mulai hubungan baru**\nPilih role untukku:",
                reply_markup=reply_markup
            )
            return SELECTING_ROLE
        
        return ConversationHandler.END


# ===================== MAIN FUNCTION =====================

def main():
    """Main function"""
    bot = GadisUltimateV56()
    
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    # Conversation handlers
    start_conv = ConversationHandler(
        entry_points=[CommandHandler('start', bot.start_command)],
        states={
            0: [CallbackQueryHandler(bot.start_pause_callback, pattern='^(unpause|new)$')],
            SELECTING_ROLE: [CallbackQueryHandler(bot.role_callback, pattern='^role_')],
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )
    
    end_conv = ConversationHandler(
        entry_points=[CommandHandler('end', bot.end_command)],
        states={
            CONFIRM_END: [CallbackQueryHandler(bot.end_callback, pattern='^end_')],
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )
    
    # Add handlers
    app.add_handler(start_conv)
    app.add_handler(end_conv)
    app.add_handler(CommandHandler("status", bot.status_command))
    app.add_handler(CommandHandler("dominant", bot.dominant_command))
    app.add_handler(CommandHandler("pause", bot.pause_command))
    app.add_handler(CommandHandler("unpause", bot.unpause_command))
    app.add_handler(CommandHandler("help", bot.help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.error(f"Error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "*maaf* ada error kecil. coba lagi ya..."
            )
    
    app.add_error_handler(error_handler)
    
    print("\n" + "="*80)
    print("🚀 GADIS ULTIMATE V56.0 - THE PERFECT HUMAN")
    print("="*80)
    print("\n✅ **SEMUA FITUR AKTIF:**")
    print("  • 20+ Mood System")
    print("  • Dominant/Submissive Mode")
    print("  • Agresif saat Horny")
    print("  • Sensitive Areas")
    print("  • Arousal & Wetness")
    print("  • Fast Leveling (45 menit)")
    print("  • AI Natural dengan DeepSeek")
    print("  • Memory System")
    print("\n📝 /start untuk memulai")
    print("📊 /status untuk lihat progress")
    print("\n" + "="*80)
    
    app.run_polling()

if __name__ == "__main__":
    main()
