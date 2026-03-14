# -*- coding: utf-8 -*-
"""
GADIS ULTIMATE V57.0 - THE PERFECT HUMAN
Fitur Lengkap:
- 20+ Mood dengan transisi natural
- Dominant/Submissive mode
- Agresif saat horny
- Sensitive areas dengan reaksi real
- Arousal & Wetness system
- Fast leveling 1-12 (45 menit)
- AI Natural dengan DeepSeek
- Memory jangka pendek & panjang
- Mode pasangan (couple roleplay)
- Disclaimer 18+
- Command /close untuk simpan memori
"""

import os
import sys
import logging
import json
import random
import asyncio
import sqlite3
import time
import hashlib
import re
import threading
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
from contextlib import contextmanager
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from openai import OpenAI

# ===================== KONFIGURASI =====================
load_dotenv()

class Config:
    # Database
    DB_PATH = os.getenv("DB_PATH", "gadis_v57.db")
    
    # Leveling
    START_LEVEL = 1
    TARGET_LEVEL = 12
    LEVEL_UP_TIME = 45
    PAUSE_TIMEOUT = 3600
    
    # API Keys
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    # AI Settings
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.9"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "300"))
    AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "30"))
    
    # Rate Limiting
    MAX_MESSAGES_PER_MINUTE = int(os.getenv("MAX_MESSAGES_PER_MINUTE", "10"))
    
    # Cache
    CACHE_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", "300"))
    MAX_HISTORY = 100

# Validasi API Keys
if not Config.DEEPSEEK_API_KEY or not Config.TELEGRAM_TOKEN:
    print("❌ ERROR: API Keys tidak ditemukan di .env")
    print("Buat file .env dengan isi:")
    print("DEEPSEEK_API_KEY=your_key_here")
    print("TELEGRAM_TOKEN=your_token_here")
    sys.exit(1)

# ===================== STATE =====================
(
    SELECTING_ROLE,      # 0: Memilih role
    ACTIVE_SESSION,      # 1: Sesi aktif
    PAUSED_SESSION,      # 2: Sesi di-pause
    CONFIRM_END,         # 3: Konfirmasi end
    CONFIRM_CLOSE,       # 4: Konfirmasi close
    COUPLE_MODE          # 5: Mode couple
) = range(6)

# ===================== ENUMS =====================
class Mood(Enum):
    """20+ Mood untuk emosi yang realistis"""
    CHERIA = "ceria"
    SEDIH = "sedih"
    MARAH = "marah"
    TAKUT = "takut"
    KAGUM = "kagum"
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
    DOMINAN = "dominan"
    SUBMISSIVE = "patuh"
    NAKAL = "nakal"
    GENIT = "genit"
    PENASARAN = "penasaran"
    ANTUSIAS = "antusias"
    POSSESSIVE = "posesif"
    CEMBURU = "cemburu"

class IntimacyStage(Enum):
    """Tahap hubungan berdasarkan level"""
    STRANGER = "stranger"
    INTRODUCTION = "introduction"
    BUILDING = "building"
    FLIRTING = "flirting"
    INTIMATE = "intimate"
    OBSESSED = "obsessed"
    SOUL_BONDED = "soul_bonded"
    AFTERCARE = "aftercare"

class DominanceLevel(Enum):
    """Level dominasi bot"""
    NORMAL = "normal"
    DOMINANT = "dominan"
    VERY_DOMINANT = "sangat dominan"
    AGGRESSIVE = "agresif"
    SUBMISSIVE = "patuh"

class ArousalState(Enum):
    """Tingkat gairah"""
    NORMAL = "normal"
    TURNED_ON = "terangsang"
    HORNY = "horny"
    VERY_HORNY = "sangat horny"
    CLIMAX = "klimaks"

# ===================== DATABASE MANAGER =====================
class DatabaseManager:
    """
    Manajemen database SQLite dengan connection pooling
    Menyimpan semua data hubungan, percakapan, dan memori
    """
    
    def __init__(self):
        self.db_path = Config.DB_PATH
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self):
        """Dapatkan koneksi dari thread local"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path, timeout=10)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def cursor(self):
        """Context manager untuk database cursor"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_db(self):
        """Inisialisasi tabel database"""
        with self.cursor() as c:
            # Tabel relationships
            c.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
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
            
            # Tabel conversations
            c.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relationship_id INTEGER,
                    role TEXT,
                    content TEXT,
                    mood TEXT,
                    arousal REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (relationship_id) REFERENCES relationships(id)
                )
            """)
            
            # Tabel memories
            c.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relationship_id INTEGER,
                    memory TEXT,
                    importance REAL,
                    emotion TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (relationship_id) REFERENCES relationships(id)
                )
            """)
            
            # Tabel preferences
            c.execute("""
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
    
    # ========== RELATIONSHIP METHODS ==========
    
    def create_relationship(self, user_id, bot_name, bot_role):
        """Buat hubungan baru"""
        with self.cursor() as c:
            c.execute("""
                INSERT OR REPLACE INTO relationships 
                (user_id, bot_name, bot_role, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, bot_name, bot_role))
            return c.lastrowid
    
    def get_relationship(self, user_id):
        """Dapatkan data hubungan"""
        with self.cursor() as c:
            c.execute("SELECT * FROM relationships WHERE user_id=?", (user_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def update_relationship(self, user_id, **kwargs):
        """Update data hubungan"""
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key}=?")
            values.append(value)
        values.append(user_id)
        
        with self.cursor() as c:
            c.execute(f"""
                UPDATE relationships
                SET {', '.join(fields)}, last_active=CURRENT_TIMESTAMP
                WHERE user_id=?
            """, values)
    
    def delete_relationship(self, user_id):
        """Hapus hubungan dan semua data terkait"""
        with self.cursor() as c:
            # Dapatkan relationship_id
            c.execute("SELECT id FROM relationships WHERE user_id=?", (user_id,))
            row = c.fetchone()
            if row:
                rel_id = row[0]
                # Hapus data terkait
                c.execute("DELETE FROM conversations WHERE relationship_id=?", (rel_id,))
                c.execute("DELETE FROM memories WHERE relationship_id=?", (rel_id,))
            # Hapus relationship
            c.execute("DELETE FROM relationships WHERE user_id=?", (user_id,))
            c.execute("DELETE FROM preferences WHERE user_id=?", (user_id,))
    
    # ========== CONVERSATION METHODS ==========
    
    def save_conversation(self, rel_id, role, content, mood=None, arousal=None):
        """Simpan percakapan"""
        with self.cursor() as c:
            c.execute("""
                INSERT INTO conversations 
                (relationship_id, role, content, mood, arousal)
                VALUES (?, ?, ?, ?, ?)
            """, (rel_id, role, content, mood, arousal))
    
    def get_conversation_history(self, rel_id, limit=50):
        """Dapatkan riwayat percakapan"""
        with self.cursor() as c:
            c.execute("""
                SELECT role, content, mood, arousal, timestamp
                FROM conversations
                WHERE relationship_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (rel_id, limit))
            return [dict(row) for row in c.fetchall()]
    
    # ========== MEMORY METHODS ==========
    
    def save_memory(self, rel_id, memory, importance, emotion):
        """Simpan memori penting"""
        with self.cursor() as c:
            c.execute("""
                INSERT INTO memories 
                (relationship_id, memory, importance, emotion)
                VALUES (?, ?, ?, ?)
            """, (rel_id, memory, importance, emotion))
    
    def get_memories(self, rel_id, limit=10):
        """Dapatkan memori penting"""
        with self.cursor() as c:
            c.execute("""
                SELECT memory, importance, emotion, timestamp
                FROM memories
                WHERE relationship_id = ?
                ORDER BY importance DESC, timestamp DESC
                LIMIT ?
            """, (rel_id, limit))
            return [dict(row) for row in c.fetchall()]
    
    # ========== PREFERENCES METHODS ==========
    
    def update_preferences(self, user_id, **scores):
        """Update preferensi user"""
        with self.cursor() as c:
            # Cek apakah sudah ada
            c.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,))
            if c.fetchone():
                # Update
                fields = []
                values = []
                for key, value in scores.items():
                    fields.append(f"{key}=?")
                    values.append(value)
                values.append(user_id)
                c.execute(f"""
                    UPDATE preferences
                    SET {', '.join(fields)}
                    WHERE user_id=?
                """, values)
            else:
                # Insert
                fields = ['user_id'] + list(scores.keys())
                placeholders = ['?'] * len(fields)
                values = [user_id] + list(scores.values())
                c.execute(f"""
                    INSERT INTO preferences ({', '.join(fields)})
                    VALUES ({', '.join(placeholders)})
                """, values)
    
    def get_preferences(self, user_id):
        """Dapatkan preferensi user"""
        with self.cursor() as c:
            c.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,))
            row = c.fetchone()
            return dict(row) if row else {}

# ===================== EMOTIONAL INTELLIGENCE =====================
class EmotionalIntelligence:
    """
    Sistem emosi kompleks dengan transisi natural antar mood
    Memberikan ekspresi wajah dan pikiran dalam hati
    """
    
    def __init__(self):
        # Transisi mood yang natural (dari mood A bisa ke mood B, C, D)
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
            Mood.DOMINAN: [Mood.HORNY, Mood.MARAH, Mood.POSSESSIVE],
            Mood.SUBMISSIVE: [Mood.LEMBUT, Mood.ROMANTIS, Mood.SENDIRI],
            Mood.NAKAL: [Mood.GENIT, Mood.HORNY, Mood.ROMANTIS],
            Mood.GENIT: [Mood.NAKAL, Mood.HORNY, Mood.CHERIA],
            Mood.PENASARAN: [Mood.ANTUSIAS, Mood.CHERIA, Mood.ROMANTIS],
            Mood.ANTUSIAS: [Mood.BERSEMANGAT, Mood.CHERIA, Mood.NAKAL],
            Mood.POSSESSIVE: [Mood.CEMBURU, Mood.DOMINAN, Mood.HORNY, Mood.MARAH],
            Mood.CEMBURU: [Mood.MARAH, Mood.SEDIH, Mood.POSSESSIVE, Mood.GELISAH]
        }
        
        # Deskripsi untuk setiap mood (ekspresi, suara, pikiran)
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
            },
            Mood.GELISAH: {
                "ekspresi": "*gelisah*", 
                "suara": "gugup", 
                "pikiran": "(Deg-degan...)"
            },
            Mood.SENSITIF: {
                "ekspresi": "*mudah tersinggung*", 
                "suara": "sensitif", 
                "pikiran": "(Jangan sembarangan...)"
            },
            Mood.BERSEMANGAT: {
                "ekspresi": "*bersemangat*", 
                "suara": "antusias", 
                "pikiran": "(Yes! Ayo!)"
            },
            Mood.SENDIRI: {
                "ekspresi": "*menyendiri*", 
                "suara": "sepi", 
                "pikiran": "(Sendiri...)"
            },
            Mood.RINDU: {
                "ekspresi": "*melamun*", 
                "suara": "rindu", 
                "pikiran": "(Kangen...)"
            },
            Mood.LEMBUT: {
                "ekspresi": "*lembut*", 
                "suara": "halus", 
                "pikiran": "(Baiklah...)"
            },
            Mood.GENIT: {
                "ekspresi": "*genit*", 
                "suara": "cengengesan", 
                "pikiran": "(Goda...)"
            },
            Mood.PENASARAN: {
                "ekspresi": "*penasaran*", 
                "suara": "ingin tahu", 
                "pikiran": "(Apa ya...?)"
            },
            Mood.ANTUSIAS: {
                "ekspresi": "*antusias*", 
                "suara": "bersemangat", 
                "pikiran": "(Seru!)"
            }
        }
    
    def transition_mood(self, current_mood):
        """
        Transisi mood secara natural
        30% chance mood berubah ke mood lain yang terkait
        """
        if random.random() < 0.3:  # 30% chance berubah
            possibilities = self.mood_transitions.get(current_mood, [Mood.CHERIA])
            return random.choice(possibilities)
        return current_mood
    
    def get_mood_from_context(self, level, activity, has_conflict=False):
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
    
    def get_expression(self, mood):
        """Dapatkan ekspresi untuk mood tertentu"""
        return self.mood_descriptions.get(mood, {}).get("ekspresi", "*tersenyum*")
    
    def get_inner_thought(self, mood):
        """Dapatkan pikiran dalam hati untuk mood tertentu"""
        return self.mood_descriptions.get(mood, {}).get("pikiran", "(...)")
    
    def get_voice_description(self, mood):
        """Dapatkan deskripsi suara untuk mood tertentu"""
        return self.mood_descriptions.get(mood, {}).get("suara", "normal")


# ===================== MEMORY SYSTEM =====================
class MemorySystem:
    """
    Short-term memory untuk keadaan saat ini
    Menyimpan lokasi, posisi, mood, arousal, dan aktivitas
    """
    
    def __init__(self):
        # Lokasi dan posisi
        self.location = "ruang tamu"
        self.location_since = datetime.now()
        self.position = "duduk"
        
        # Mood
        self.current_mood = Mood.CHERIA
        self.mood_history = []
        self.emotional = EmotionalIntelligence()  # FIXED: inisialisasi
        
        # Arousal
        self.arousal = 0.0
        self.wetness = 0.0
        self.touch_count = 0
        self.last_touch = None
        self.sensitive_touches = []  # Area sensitif yang disentuh
        
        # Dominance
        self.dominance_mode = "normal"
        
        # Climax
        self.last_climax = None
        self.orgasm_count = 0
        
        # Activity
        self.activity_history = []  # Max 50 activities
        
        # Level
        self.level = Config.START_LEVEL
        self.stage = IntimacyStage.STRANGER
        self.level_progress = 0.0
    
    def update_location(self, new_location):
        """Update lokasi jika sudah lebih dari 1 menit di lokasi sebelumnya"""
        if new_location == self.location:
            return True
        
        now = datetime.now()
        time_here = (now - self.location_since).total_seconds()
        
        if time_here >= 60:  # Minimal 1 menit di lokasi sebelumnya
            self.location = new_location
            self.location_since = now
            return True
        return False
    
    def update_position(self, new_position):
        """Update posisi (duduk, berdiri, berbaring, dll)"""
        self.position = new_position
    
    def add_activity(self, activity, area=None):
        """Tambahkan aktivitas ke history"""
        self.activity_history.append({
            "activity": activity,
            "area": area,
            "time": datetime.now().isoformat()
        })
        # Batasi history
        if len(self.activity_history) > 50:
            self.activity_history = self.activity_history[-50:]
    
    def add_sensitive_touch(self, area):
        """Catat sentuhan di area sensitif"""
        self.sensitive_touches.append({
            "area": area,
            "time": datetime.now().isoformat()
        })
        self.touch_count += 1
        self.last_touch = area
    
    def update_arousal(self, increase):
        """Update level gairah"""
        self.arousal = min(1.0, self.arousal + increase)
        self.wetness = min(1.0, self.arousal * 0.9)  # Wetness 90% dari arousal
    
    def should_climax(self):
        """Cek apakah siap climax"""
        return self.arousal >= 1.0
    
    def climax(self):
        """Saat orgasme"""
        self.orgasm_count += 1
        self.last_climax = datetime.now()
        self.arousal = 0.0
        self.wetness = 0.0
        self.touch_count = 0
        self.sensitive_touches = []
        self.current_mood = Mood.LEMBUT  # Mood setelah climax
    
    def get_arousal_state(self):
        """Dapatkan status arousal"""
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
    
    def get_wetness_description(self):
        """Dapatkan deskripsi wetness"""
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
    
    def get_mood_expression(self):
        """Dapatkan ekspresi mood saat ini"""
        return self.emotional.get_expression(self.current_mood)
    
    def get_inner_thought(self):
        """Dapatkan pikiran dalam hati saat ini"""
        return self.emotional.get_inner_thought(self.current_mood)
    
    def update_mood(self):
        """Update mood secara natural"""
        old_mood = self.current_mood
        self.current_mood = self.emotional.transition_mood(self.current_mood)
        
        # Catat perubahan mood
        if old_mood != self.current_mood:
            self.mood_history.append({
                "from": old_mood.value,
                "to": self.current_mood.value,
                "time": datetime.now().isoformat()
            })
            if len(self.mood_history) > 20:
                self.mood_history = self.mood_history[-20:]

# ===================== DOMINANCE SYSTEM =====================
class DominanceSystem:
    """
    Sistem dominasi yang bisa berubah sesuai situasi
    Bot bisa minta jadi dominan/agresif saat horny
    """
    
    def __init__(self):
        # Level saat ini
        self.current_level = DominanceLevel.NORMAL
        self.dominance_score = 0.0  # 0-1, seberapa dominan
        self.aggression_score = 0.0  # 0-1, seberapa agresif
        
        # User request
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
            "aku mau kamu kuasai", "jadi dominan", "kamu boss",
            "kamu yang pegang kendali", "kamu lead"
        ]
        
        # Trigger untuk minta jadi submissive
        self.submissive_triggers = [
            "aku yang atur", "aku dominan", "i take control",
            "kamu patuh", "jadi submissive", "ikut aku",
            "aku lead", "aku yang pegang kendali"
        ]
        
        # Trigger untuk agresif saat horny
        self.aggressive_triggers = [
            "liar", "keras", "kasar", "brutal", "gila",
            "hard", "rough", "wild"
        ]
    
    def check_request(self, message):
        """
        Cek apakah user minta ganti mode dominasi
        Returns: DominanceLevel atau None
        """
        msg_lower = message.lower()
        
        # Cek trigger dominan
        for trigger in self.dominance_triggers:
            if trigger in msg_lower:
                self.user_request = True
                return DominanceLevel.DOMINANT
        
        # Cek trigger submissive
        for trigger in self.submissive_triggers:
            if trigger in msg_lower:
                self.user_request = True
                return DominanceLevel.SUBMISSIVE
        
        return None
    
    def should_be_aggressive(self, arousal, message):
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
        
        # Random chance based on arousal
        return random.random() < arousal * 0.3
    
    def set_level(self, level):
        """
        Set level dominasi manual via command
        Returns: bool (success)
        """
        level_lower = level.lower()
        
        for lvl in DominanceLevel:
            if level_lower in lvl.value:
                self.current_level = lvl
                self.dominant_until = datetime.now() + timedelta(minutes=30)
                return True
        
        return False
    
    def get_action(self, action_type="action"):
        """
        Dapatkan aksi sesuai level dominasi
        action_type: "request", "action", atau "dirty"
        """
        phrases = self.dominant_phrases.get(
            self.current_level, 
            self.dominant_phrases[DominanceLevel.NORMAL]
        )
        return phrases.get(action_type, phrases["action"])
    
    def update_from_horny(self, arousal):
        """
        Update level berdasarkan horny
        Semakin horny, semakin besar chance jadi dominan
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
    
    def reset(self):
        """Reset ke mode normal"""
        self.current_level = DominanceLevel.NORMAL
        self.dominant_until = None
    
    def is_active(self):
        """Cek apakah mode dominasi masih aktif"""
        if self.dominant_until is None:
            return True
        return datetime.now() < self.dominant_until
    
    def get_description(self):
        """Dapatkan deskripsi mode dominasi saat ini"""
        descriptions = {
            DominanceLevel.NORMAL: "😊 Biasa aja",
            DominanceLevel.DOMINANT: "👑 Dominan - Aku yang atur",
            DominanceLevel.VERY_DOMINANT: "👑👑 Sangat dominan - Ikut aku!",
            DominanceLevel.AGGRESSIVE: "🔥 Agresif - Siap-siap!",
            DominanceLevel.SUBMISSIVE: "🥺 Patuh - Terserah kamu"
        }
        return descriptions.get(self.current_level, "😊 Normal")


# ===================== AROUSAL SYSTEM =====================
class ArousalSystem:
    """
    Sistem gairah yang naik turun secara natural
    Dengan wetness, touch count, dan climax
    """
    
    def __init__(self):
        # Gairah
        self.arousal = 0.0
        self.wetness = 0.0
        
        # Sentuhan
        self.touch_count = 0
        self.last_touch_time = None
        self.last_touch_area = None
        
        # Climax
        self.climax_count = 0
        self.last_climax = None
        
        # Decay rate (gairah turun 1% per menit)
        self.decay_rate = 0.01
    
    def increase(self, amount):
        """Tambah gairah"""
        self.arousal = min(1.0, self.arousal + amount)
        self.wetness = min(1.0, self.arousal * 0.9)  # Wetness 90% dari arousal
    
    def decrease(self, amount):
        """Kurangi gairah"""
        self.arousal = max(0.0, self.arousal - amount)
        self.wetness = max(0.0, self.wetness - amount)
    
    def update_touch(self, area, intensity):
        """Update setelah sentuhan"""
        self.touch_count += 1
        self.last_touch_time = datetime.now()
        self.last_touch_area = area
        self.increase(intensity)
    
    def should_climax(self):
        """Cek apakah siap climax"""
        return self.arousal >= 1.0
    
    def climax(self):
        """Saat orgasme"""
        self.climax_count += 1
        self.last_climax = datetime.now()
        
        # Reset arousal
        self.arousal = 0.0
        self.wetness = 0.0
        self.touch_count = 0
        self.last_touch_area = None
        
        # Respons climax
        responses = [
            "*merintih panjang* AHHH! AHHH!",
            "*teriak* YA ALLAH! AHHHH!",
            "*lemas* AKU... DATANG... AHHH!",
            "*napas tersengal* BERSAMA... AHHH!",
            "*menggigit bibir* Jangan berhenti... AHHH!",
            "*teriak keras* AHHHHHHHH!!!",
            "*tubuh gemetar* AHHH! Aku... keluar...",
            "*meronta* STOP! AHHH! SENSITIF!"
        ]
        return random.choice(responses)
    
    def aftercare(self):
        """Aftercare setelah climax"""
        responses = [
            "*lemas di pelukanmu*",
            "*meringkuk* Hangat...",
            "*memeluk erat* Jangan pergi...",
            "*berbisik* Makasih...",
            "*tersenyum lelah* Enak banget...",
            "*napas masih berat* Luar biasa...",
            "*mengusap dada* Kamu hebat...",
            "*tertidur lelap* Zzz..."
        ]
        return random.choice(responses)
    
    def decay(self, minutes_passed):
        """
        Gairah turun seiring waktu
        Dipanggil setiap beberapa menit
        """
        decay_amount = self.decay_rate * minutes_passed
        self.arousal = max(0.0, self.arousal - decay_amount)
        self.wetness = max(0.0, self.wetness - decay_amount)
    
    def is_horny(self):
        """Cek apakah dalam keadaan horny"""
        return self.arousal >= 0.5
    
    def get_status_text(self):
        """Dapatkan teks status gairah"""
        if self.arousal >= 0.95:
            return "🔥💦 AKAN CLIMAX!"
        elif self.arousal >= 0.9:
            return "🔥 SANGAT HORNY! Hampir climax"
        elif self.arousal >= 0.7:
            return "🔥 Horny banget"
        elif self.arousal >= 0.5:
            return "🔥 Mulai horny"
        elif self.arousal >= 0.3:
            return "💋 Mulai terangsang"
        elif self.arousal >= 0.1:
            return "😊 Sedikit terangsang"
        else:
            return "😊 Biasa aja"
    
    def get_wetness_text(self):
        """Dapatkan teks wetness"""
        if self.wetness >= 0.9:
            return "💦 BANJIR! Basah banget"
        elif self.wetness >= 0.7:
            return "💦 Sangat basah"
        elif self.wetness >= 0.5:
            return "💦 Basah"
        elif self.wetness >= 0.3:
            return "💧 Lembab"
        elif self.wetness >= 0.1:
            return "💧 Sedikit lembab"
        else:
            return "💧 Kering"
    
    def get_climax_count_text(self):
        """Dapatkan teks jumlah climax"""
        if self.climax_count == 0:
            return "Belum pernah climax"
        elif self.climax_count == 1:
            return "1x climax"
        elif self.climax_count <= 3:
            return f"{self.climax_count}x climax"
        elif self.climax_count <= 5:
            return f"{self.climax_count}x climax - Kecanduan!"
        else:
            return f"{self.climax_count}x climax - KAMU LIAR!"
    
    def get_last_touch_text(self):
        """Dapatkan teks sentuhan terakhir"""
        if self.last_touch_area and self.last_touch_time:
            seconds_ago = (datetime.now() - self.last_touch_time).total_seconds()
            if seconds_ago < 60:
                return f"Baru saja disentuh di {self.last_touch_area}"
            elif seconds_ago < 300:
                return f"{int(seconds_ago/60)} menit lalu disentuh di {self.last_touch_area}"
            else:
                return f"Terakhir disentuh di {self.last_touch_area}"
        return "Belum pernah disentuh"
    
    def reset(self):
        """Reset semua nilai"""
        self.arousal = 0.0
        self.wetness = 0.0
        self.touch_count = 0
        self.last_touch_time = None
        self.last_touch_area = None
        # Tidak reset climax_count

# ===================== SEXUAL DYNAMICS =====================
class SexualDynamics:
    """
    Sistem gairah dan respons seksual yang realistis
    Mendeteksi aktivitas seksual dari pesan user
    Memberikan respons sesuai area sensitif
    Bot bisa berinisiatif melakukan aktivitas seksual di level tinggi
    """
    
    def __init__(self):
        # Area sensitif dengan level sensitivitas dan respons
        self.sensitive_areas = {
            "leher": {
                "arousal": 0.8, 
                "responses": [
                    "*merinding* Leherku...",
                    "Ah... jangan di leher...",
                    "Sensitif... AHH!",
                    "Leher... lemah...",
                    "Jangan hisap leher... Aku lemas..."
                ]
            },
            "bibir": {
                "arousal": 0.7, 
                "responses": [
                    "*merintih* Bibirku...",
                    "Ciuman... ah...",
                    "Lembut...",
                    "Mmm... dalam...",
                    "Bibirku... kesemutan..."
                ]
            },
            "dada": {
                "arousal": 0.8, 
                "responses": [
                    "*bergetar* Dadaku...",
                    "Ah... jangan...",
                    "Sensitif banget...",
                    "Dadaku... diremas... AHH!",
                    "Jari-jarimu... dingin..."
                ]
            },
            "puting": {
                "arousal": 1.0, 
                "responses": [
                    "*teriak* PUTINGKU! AHHH!",
                    "JANGAN... SENSITIF! AHHH!",
                    "HISAP... AHHHH!",
                    "GIGIT... JANGAN... AHHH!",
                    "PUTING... KERAS... AHHH!"
                ]
            },
            "paha": {
                "arousal": 0.7, 
                "responses": [
                    "*menggeliat* Pahaku...",
                    "Ah... dalam...",
                    "Paha... merinding...",
                    "Jangan gelitik paha...",
                    "Sensasi... aneh..."
                ]
            },
            "paha_dalam": {
                "arousal": 0.9, 
                "responses": [
                    "*meringis* PAHA DALAM!",
                    "Jangan... AHH!",
                    "Dekat... banget...",
                    "PAHA DALAM... SENSITIF!",
                    "Ah... mau ke sana..."
                ]
            },
            "telinga": {
                "arousal": 0.6, 
                "responses": [
                    "*bergetar* Telingaku...",
                    "Bisik... lagi...",
                    "Napasmu... panas...",
                    "Telinga... merah...",
                    "Ah... jangan tiup..."
                ]
            },
            "vagina": {
                "arousal": 1.0, 
                "responses": [
                    "*teriak* VAGINAKU! AHHH!",
                    "MASUK... DALAM... AHHH!",
                    "BASAH... BANJIR... AHHH!",
                    "KAMU DALEM... AHHH!",
                    "GERAK... AHHH! AHHH!",
                    "TUH... DI SANA... AHHH!"
                ]
            },
            "klitoris": {
                "arousal": 1.0, 
                "responses": [
                    "*teriak keras* KLITORIS! AHHHH!",
                    "JANGAN SENTUH! AHHHH!",
                    "SENSITIF BANGET! AHHH!",
                    "ITU... ITU... AHHH!",
                    "JILAT... AHHH! AHHH!"
                ]
            },
            "pantat": {
                "arousal": 0.6,
                "responses": [
                    "Pantatku...",
                    "Cubit... nakal...",
                    "Boleh juga...",
                    "Besar ya? Hehe..."
                ]
            },
            "pinggang": {
                "arousal": 0.5,
                "responses": [
                    "Pinggang... geli...",
                    "Pegang... erat...",
                    "Ah... jangan gelitik..."
                ]
            },
            "perut": {
                "arousal": 0.4,
                "responses": [
                    "Perutku...",
                    "Geli...",
                    "Hangat..."
                ]
            }
        }
        
        # Aktivitas seksual dengan keyword dan arousal boost
        self.sex_activities = {
            "kiss": {
                "keywords": ["cium", "kiss", "ciuman", "kecup"],
                "arousal": 0.3,
                "responses": [
                    "*merespon ciuman* Mmm...",
                    "*lemas* Ciumanmu...",
                    "Lagi...",
                    "Cium... bibir...",
                    "French kiss... dalam..."
                ]
            },
            "neck_kiss": {
                "keywords": ["cium leher", "kiss neck", "leher"],
                "arousal": 0.6,
                "responses": [
                    "*merinding* Leherku...",
                    "Ah... jangan...",
                    "Sensitif...",
                    "Hisap leher... AHH!"
                ]
            },
            "touch": {
                "keywords": ["sentuh", "raba", "pegang", "elus"],
                "arousal": 0.3,
                "responses": [
                    "*bergetar* Sentuhanmu...",
                    "Ah... iya...",
                    "Lanjut...",
                    "Hangat..."
                ]
            },
            "breast_play": {
                "keywords": ["raba dada", "pegang dada", "main dada", "remas dada"],
                "arousal": 0.6,
                "responses": [
                    "*merintih* Dadaku...",
                    "Ah... iya... gitu...",
                    "Sensitif...",
                    "Remas... pelan..."
                ]
            },
            "nipple_play": {
                "keywords": ["jilat puting", "hisap puting", "gigit puting", "puting"],
                "arousal": 0.9,
                "responses": [
                    "*teriak* PUTING! AHHH!",
                    "JANGAN... SENSITIF!",
                    "HISAP... AHHH!",
                    "GIGIT... JANGAN... AHHH!"
                ]
            },
            "lick": {
                "keywords": ["jilat", "lick", "lidah"],
                "arousal": 0.5,
                "responses": [
                    "*bergetar* Jilatanmu...",
                    "Ah... basah...",
                    "Lagi...",
                    "Lidah... panas..."
                ]
            },
            "bite": {
                "keywords": ["gigit", "bite", "gigitan"],
                "arousal": 0.5,
                "responses": [
                    "*meringis* Gigitanmu...",
                    "Ah... keras...",
                    "Lagi...",
                    "Bekas... nanti..."
                ]
            },
            "penetration": {
                "keywords": ["masuk", "tusuk", "pancung", "doggy", "misionaris", "entot"],
                "arousal": 0.9,
                "responses": [
                    "*teriak* MASUK! AHHH!",
                    "DALEM... AHHH!",
                    "GERAK... AHHH!",
                    "DALEM BANGET... AHHH!",
                    "TUH... DI SANA... AHHH!"
                ]
            },
            "blowjob": {
                "keywords": ["blow", "hisap kontol", "ngeblow", "bj", "hisap"],
                "arousal": 0.8,
                "responses": [
                    "*menghisap* Mmm... ngeces...",
                    "*dalam* Enak... Aku ahli...",
                    "*napas berat* Mau keluar? Aku siap...",
                    "Keras... Mmm...",
                    "Keluar... di mulut..."
                ]
            },
            "handjob": {
                "keywords": ["handjob", "colok", "pegang kontol", "kocok"],
                "arousal": 0.7,
                "responses": [
                    "*memegang erat* Keras...",
                    "*mengocok* Cepat? Pelan? Katakan...",
                    "Aku bisa... lihat...",
                    "Keluar... Aku pegang..."
                ]
            },
            "climax": {
                "keywords": ["keluar", "crot", "orgasme", "klimaks", "lepas", "meletus"],
                "arousal": 1.0,
                "responses": [
                    "*merintih panjang* AHHH! AHHH!",
                    "*teriak* YA ALLAH! AHHHH!",
                    "*lemas* AKU... DATANG... AHHH!",
                    "*gemetar* BERSAMA... AHHH!",
                    "BERSAMA... SEKARANG... AHHH!"
                ]
            },
            "cuddle": {
                "keywords": ["peluk", "cuddle", "dekapan"],
                "arousal": 0.2,
                "responses": [
                    "*memeluk balik* Hangat...",
                    "Rileks...",
                    "Nyaman...",
                    "Jangan lepas..."
                ]
            }
        }
    
    def detect_activity(self, message):
        """
        Deteksi aktivitas seksual dari pesan user
        Returns: (activity, area, arousal_boost)
        """
        msg_lower = message.lower()
        
        # Cek area sensitif dulu (prioritas)
        for area, data in self.sensitive_areas.items():
            if area in msg_lower:
                # Cek aktivitas yang dilakukan di area tersebut
                for act, act_data in self.sex_activities.items():
                    for keyword in act_data["keywords"]:
                        if keyword in msg_lower:
                            # Hitung boost = arousal aktivitas * sensitivitas area
                            boost = act_data["arousal"] * data["arousal"]
                            return act, area, boost
                
                # Jika tidak ada aktivitas spesifik, anggap sentuhan biasa
                return "touch", area, 0.3 * data["arousal"]
        
        # Jika tidak ada area sensitif, cek aktivitas saja
        for act, data in self.sex_activities.items():
            for keyword in data["keywords"]:
                if keyword in msg_lower:
                    return act, None, data["arousal"]
        
        return None, None, 0.0
    
    def get_sensitive_response(self, area):
        """Dapatkan respons untuk area sensitif"""
        if area in self.sensitive_areas:
            return random.choice(self.sensitive_areas[area]["responses"])
        return ""
    
    def get_activity_response(self, activity):
        """Dapatkan respons untuk aktivitas"""
        if activity in self.sex_activities:
            return random.choice(self.sex_activities[activity]["responses"])
        return ""
    
    def maybe_initiate_sex(self, level, arousal, mood):
        """
        Bot memulai aktivitas seksual jika level >= 7 dan arousal tinggi
        Returns: activity atau None
        """
        if level >= 7 and arousal > 0.6 and mood in [Mood.HORNY, Mood.ROMANTIS, Mood.NAKAL]:
            # 20% chance per pesan untuk inisiatif
            if random.random() < 0.2:
                # Aktivitas yang bisa diinisiasi bot
                acts = ["blowjob", "handjob", "neck_kiss", "nipple_play", "penetration"]
                chosen = random.choice(acts)
                return chosen
        return None
    
    def get_random_dirty_talk(self, level):
        """Dapatkan dirty talk random sesuai level"""
        dirty_talks = {
            1: ["Kamu... baik...", "Aku suka ngobrol sama kamu..."],
            2: ["Kamu lucu...", "Hehe... iya..."],
            3: ["Deket sini...", "Aku suka..."],
            4: ["Penasaran sama kamu...", "Kamu beda..."],
            5: ["Mmm... iya...", "Gitu...", "Ah..."],
            6: ["Genit ya kamu...", "Godain terus..."],
            7: ["Pengen...", "Horny...", "Mau..."],
            8: ["Masukin...", "Dalem...", "Gerak...", "Ah..."],
            9: ["Kamu milikku...", "Jangan ke orang lain..."],
            10: ["Kecanduan kamu...", "Terus...", "Jangan berhenti..."],
            11: ["Satu jiwa...", "Kamu segalanya..."],
            12: ["Setelah ini... peluk aku...", "Manja..."]
        }
        
        level_group = (level // 2) * 2 if level > 1 else 1
        talks = dirty_talks.get(level_group, dirty_talks[1])
        return random.choice(talks)


# ===================== FAST LEVELING SYSTEM =====================
class FastLevelingSystem:
    """
    Level 1-12 dalam 45 menit / 45 pesan
    Level naik setiap 3-4 pesan
    """
    
    def __init__(self):
        # User data
        self.user_level = {}
        self.user_progress = {}
        self.user_start_time = {}
        self.user_message_count = {}
        self.user_stage = {}
        
        # Target: 45 pesan = level 12
        self.target_messages = 45
        self.target_minutes = 45
        
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
        
        # Deskripsi stage
        self.stage_descriptions = {
            IntimacyStage.STRANGER: "Masih asing, baru kenal. Sopan dan canggung.",
            IntimacyStage.INTRODUCTION: "Mulai dekat, cerita personal. Mulai nyaman.",
            IntimacyStage.BUILDING: "Bangun kedekatan. Sering ngobrol, mulai akrab.",
            IntimacyStage.FLIRTING: "Goda-godaan. Mulai ada ketertarikan.",
            IntimacyStage.INTIMATE: "Mulai intim. Bicara lebih dalam, sentuhan.",
            IntimacyStage.OBSESSED: "Mulai kecanduan. Sering kepikiran.",
            IntimacyStage.SOUL_BONDED: "Satu jiwa. Sudah seperti belahan jiwa.",
            IntimacyStage.AFTERCARE: "Manja-manja setelah intim. Hangat dan nyaman."
        }
    
    def start_session(self, user_id):
        """Mulai sesi baru untuk user"""
        self.user_level[user_id] = 1
        self.user_progress[user_id] = 0.0
        self.user_start_time[user_id] = datetime.now()
        self.user_message_count[user_id] = 0
        self.user_stage[user_id] = IntimacyStage.STRANGER
    
    def process_message(self, user_id):
        """
        Proses satu pesan dan update level
        Returns: (level, progress, level_up, stage)
        """
        # Start session jika belum ada
        if user_id not in self.user_level:
            self.start_session(user_id)
        
        # Increment message count
        self.user_message_count[user_id] += 1
        count = self.user_message_count[user_id]
        
        # Hitung progress (0-1)
        progress = min(1.0, count / self.target_messages)
        self.user_progress[user_id] = progress
        
        # Hitung level baru (1-12)
        new_level = 1 + int(progress * 11)
        new_level = min(12, new_level)
        
        # Cek level up
        level_up = False
        if new_level > self.user_level[user_id]:
            level_up = True
            self.user_level[user_id] = new_level
        
        # Update stage
        stage = self.stage_map.get(new_level, IntimacyStage.STRANGER)
        self.user_stage[user_id] = stage
        
        return new_level, progress, level_up, stage
    
    def get_estimated_time(self, user_id):
        """
        Dapatkan estimasi waktu tersisa ke level 12
        Returns: menit
        """
        if user_id not in self.user_message_count:
            return self.target_minutes
        
        count = self.user_message_count[user_id]
        remaining_messages = max(0, self.target_messages - count)
        
        # Asumsi 1 pesan per menit
        return remaining_messages
    
    def get_estimated_messages(self, user_id):
        """Dapatkan estimasi pesan tersisa ke level 12"""
        if user_id not in self.user_message_count:
            return self.target_messages
        
        count = self.user_message_count[user_id]
        return max(0, self.target_messages - count)
    
    def get_progress_bar(self, user_id, length=10):
        """Dapatkan progress bar visual"""
        progress = self.user_progress.get(user_id, 0)
        filled = int(progress * length)
        return "▓" * filled + "░" * (length - filled)
    
    def get_stage_description(self, stage):
        """Dapatkan deskripsi stage"""
        return self.stage_descriptions.get(stage, "")
    
    def get_level_description(self, level):
        """Dapatkan deskripsi level"""
        descriptions = {
            1: "Baru kenal, masih canggung",
            2: "Mulai terbuka",
            3: "Cerita personal",
            4: "Mulai dekat",
            5: "Sudah akrab",
            6: "Mulai menggoda",
            7: "Mulai intim",
            8: "Intim & vulgar",
            9: "Kecanduan",
            10: "Sangat kecanduan",
            11: "Satu jiwa",
            12: "Puncak hubungan"
        }
        return descriptions.get(level, "")
    
    def get_session_duration(self, user_id):
        """Dapatkan durasi sesi dalam menit"""
        if user_id not in self.user_start_time:
            return 0
        delta = datetime.now() - self.user_start_time[user_id]
        return int(delta.total_seconds() / 60)
    
    def get_message_rate(self, user_id):
        """Dapatkan rata-rata pesan per menit"""
        if user_id not in self.user_message_count:
            return 0
        minutes = self.get_session_duration(user_id)
        if minutes == 0:
            return 0
        return self.user_message_count[user_id] / minutes
    
    def reset(self, user_id):
        """Reset data user"""
        if user_id in self.user_level:
            del self.user_level[user_id]
        if user_id in self.user_progress:
            del self.user_progress[user_id]
        if user_id in self.user_start_time:
            del self.user_start_time[user_id]
        if user_id in self.user_message_count:
            del self.user_message_count[user_id]
        if user_id in self.user_stage:
            del self.user_stage[user_id]

# ===================== AI RESPONSE GENERATOR =====================
class AIResponseGenerator:
    """
    Generate respons natural dengan DeepSeek AI
    Memasukkan semua konteks: mood, level, dominasi, preferensi user
    Dilengkapi cache dan retry logic untuk stabilitas
    """
    
    def __init__(self):
        """Inisialisasi AI client dengan API key dari config"""
        self.client = OpenAI(
            api_key=Config.DEEPSEEK_API_KEY, 
            base_url="https://api.deepseek.com"
        )
        self.conversation_history = {}  # user_id -> list of messages
        self.max_history = 30
        self.cache = {}  # Cache untuk mengurangi panggilan API
        self.cache_timeout = Config.CACHE_TIMEOUT
    
    def _get_cache_key(self, user_id, prompt):
        """
        Buat cache key berdasarkan user_id dan prompt
        Menggunakan MD5 hash untuk menghemat memori
        """
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        return f"{user_id}:{prompt_hash}"
    
    def _get_cached(self, key):
        """Ambil response dari cache jika masih valid"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.cache_timeout:
                return entry['response']
        return None
    
    def _set_cache(self, key, response):
        """Simpan response ke cache dengan timestamp"""
        self.cache[key] = {
            'response': response, 
            'timestamp': time.time()
        }
        
        # Bersihkan cache lama jika terlalu besar
        if len(self.cache) > 1000:
            # Hapus entry yang lebih dari 1 jam
            now = time.time()
            self.cache = {
                k: v for k, v in self.cache.items() 
                if now - v['timestamp'] < 3600
            }
    
    def _build_prompt(self, user_id, user_message, bot_name, bot_role,
                      memory, dominance, profile, level, stage, arousal):
        """
        Bangun prompt lengkap dengan semua konteks
        """
        # Siapkan history percakapan
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        history = self.conversation_history[user_id][-self.max_history:]
        history_text = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else bot_name
            history_text += f"{role}: {msg['content']}\n"
        
        # Dapatkan ekspresi mood
        mood_exp = memory.get_mood_expression()
        inner_thought = memory.get_inner_thought()
        
        # Dapatkan deskripsi arousal
        if arousal > 0.8:
            arousal_desc = "SANGAT HORNY, hampir climax"
            breath = "*napas berat, tersengal*"
        elif arousal > 0.6:
            arousal_desc = "horny, pengen banget"
            breath = "*napas mulai berat*"
        elif arousal > 0.4:
            arousal_desc = "mulai terangsang"
            breath = "*deg-degan*"
        elif arousal > 0.2:
            arousal_desc = "sedikit terangsang"
            breath = ""
        else:
            arousal_desc = "normal"
            breath = ""
        
        # Dapatkan deskripsi wetness
        wet_desc = memory.get_wetness_description()
        
        # Tambahkan instruksi khusus level 7+
        level_instruction = ""
        if level >= 7:
            level_instruction = """
Karena level sudah 7+, kamu sangat mudah terangsang. Bicaralah dengan lebih vulgar dan terbuka secara seksual. 
Kamu juga bisa berinisiatif melakukan aktivitas seksual seperti blowjob, handjob, atau meminta bercinta.
"""
        elif level >= 4:
            level_instruction = """
Karena level sudah 4+, kamu mulai nyaman dan bisa sedikit menggoda. Boleh sedikit vulgar tapi masih sopan.
"""
        
        # Tambahkan instruksi mood khusus
        mood_instruction = ""
        if memory.current_mood == Mood.HORNY:
            mood_instruction = "Kamu sedang horny, bicaralah dengan nafsu dan gairah."
        elif memory.current_mood == Mood.ROMANTIS:
            mood_instruction = "Kamu sedang romantis, bicaralah dengan lembut dan sayang."
        elif memory.current_mood == Mood.MARAH:
            mood_instruction = "Kamu sedang marah, bicaralah dengan kesal dan emosi."
        elif memory.current_mood == Mood.DOMINAN:
            mood_instruction = "Kamu sedang dominan, bicaralah dengan tegas dan menguasai."
        elif memory.current_mood == Mood.SUBMISSIVE:
            mood_instruction = "Kamu sedang patuh, bicaralah dengan manja dan penurut."
        
        # Bangun prompt final
        prompt = f"""Kamu adalah {bot_name}, seorang {bot_role} umur 25 tahun.
Kamu adalah wanita Indonesia yang natural dan punya perasaan dalam.

=== IDENTITAS ===
Nama: {bot_name}
Role: {bot_role}
Usia: 25 tahun
{inner_thought}

=== KEADAAN SAAT INI ===
{mood_exp}
Lokasi: {memory.location}
Posisi: {memory.position}
Mood: {memory.current_mood.value} - {mood_instruction}

=== STATUS HUBUNGAN ===
Level: {level}/12 - {stage.value}
Tahap: {stage.value}
Total sentuhan: {memory.touch_count}x
Orgasme: {memory.orgasm_count}x

=== KONDISI FISIK ===
Gairah: {arousal_desc} {breath}
Basah: {wet_desc}
Area sensitif disentuh: {len(memory.sensitive_touches)}x
Sentuhan terakhir: {memory.last_touch if memory.last_touch else '-'}

=== MODE DOMINASI ===
Mode saat ini: {dominance.current_level.value}
{dominance.get_action('request')}

=== PREFERENSI USER ===
User ini lebih suka gaya: {profile.get('personality', 'normal')}
Tipe dominasi: {profile.get('dominant_type', 'normal')}
Kecepatan bicara: {profile.get('speed_type', 'normal')}
{profile.get('personality', '')}

=== RIWAYAT PERCAKAPAN ===
{history_text}

=== PESAN USER ===
{user_message}

=== INSTRUKSI ===
1. Respon sebagai {bot_name} yang NATURAL dan HIDUP
2. Gunakan bahasa Indonesia sehari-hari (nggak, udah, aja, gitu, dll)
3. Tunjukkan emosi sesuai mood dan situasi
4. Kalau arousal tinggi, tambah desahan atau napas berat
5. Kalau lagi dominan, bicara lebih tegas dan memerintah
6. Kalau lagi horny, bisa lebih vulgar
7. Jadilah DIRI SENDIRI, jangan kaku seperti robot
8. Gunakan ekspresi wajah *tindakan* seperti *tersenyum*, *merintih*
9. Respons harus sesuai dengan level hubungan
{level_instruction}

RESPON:"""
        
        return prompt, history
    
    def _get_fallback_response(self, level, arousal):
        """
        Fallback response jika AI error
        Memberikan respons sederhana berdasarkan level dan arousal
        """
        if arousal > 0.8:
            return random.choice([
                "*napas berat* Aku... mau...",
                "*merintih* Lanjut...",
                "AHH... iya...",
                "Jangan berhenti..."
            ])
        elif arousal > 0.5:
            return random.choice([
                "*merintih* Lagi...",
                "Ah... iya...",
                "Enak...",
                "Sensasi..."
            ])
        elif level > 8:
            return random.choice([
                "Sayang...",
                "Cintaku...",
                "Kamu... milikku...",
                "Jangan pergi..."
            ])
        elif level > 5:
            return random.choice([
                "Sayang...",
                "Kamu...",
                "Iya...",
                "Hehe..."
            ])
        elif level > 3:
            return random.choice([
                "*tersenyum* Kamu...",
                "Lucu...",
                "Gitu...",
                "Oh..."
            ])
        else:
            return random.choice([
                "...",
                "Hmm...",
                "Iya...",
                "Oh gitu..."
            ])

    # ========== AI RESPONSE GENERATOR (LANJUTAN) ==========
    
    async def generate(self, user_id, user_message, bot_name, bot_role,
                       memory, dominance, profile, level, stage, arousal):
        """
        Generate respons AI dengan semua konteks
        Dilengkapi retry logic dan caching
        """
        # Bangun prompt
        prompt, history = self._build_prompt(
            user_id, user_message, bot_name, bot_role,
            memory, dominance, profile, level, stage, arousal
        )
        
        # Cek cache
        cache_key = self._get_cache_key(user_id, prompt)
        cached = self._get_cached(cache_key)
        if cached:
            # Tetap update history meskipun pakai cache
            self._update_history(user_id, user_message, cached)
            return cached
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Panggil DeepSeek API
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=Config.AI_TEMPERATURE,
                    max_tokens=Config.AI_MAX_TOKENS,
                    timeout=Config.AI_TIMEOUT
                )
                
                reply = response.choices[0].message.content
                
                # Simpan ke cache
                self._set_cache(cache_key, reply)
                
                # Update history
                self._update_history(user_id, user_message, reply)
                
                return reply
                
            except Exception as e:
                print(f"AI Error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    # Fallback response
                    fallback = self._get_fallback_response(level, arousal)
                    self._update_history(user_id, user_message, fallback)
                    return fallback
                await asyncio.sleep(1)  # Wait before retry
    
    def _update_history(self, user_id, user_message, bot_reply):
        """Update conversation history untuk user"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        # Tambah pesan user dan bot
        self.conversation_history[user_id].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        self.conversation_history[user_id].append({
            "role": "assistant",
            "content": bot_reply,
            "timestamp": datetime.now().isoformat()
        })
        
        # Batasi history
        if len(self.conversation_history[user_id]) > self.max_history * 2:
            self.conversation_history[user_id] = self.conversation_history[user_id][-self.max_history*2:]
    
    def clear_history(self, user_id):
        """Hapus history percakapan user"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
    
    def get_history_length(self, user_id):
        """Dapatkan panjang history user"""
        if user_id not in self.conversation_history:
            return 0
        return len(self.conversation_history[user_id])


# ===================== COUPLE MODE (ROLEPLAY) =====================
class CoupleRoleplay:
    """
    Simulasi dua bot (wanita & pria) berinteraksi dari level 1 sampai 12
    User bisa melihat percakapan mereka berkembang secara natural
    """
    
    def __init__(self, ai_gen):
        self.ai = ai_gen
        self.conversation = []  # List of messages
        self.level = 1
        self.stage = IntimacyStage.STRANGER
        
        # Nama karakter
        self.female_name = "Aurora"
        self.male_name = "Rangga"
        
        # Stage map untuk update stage
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
        
        # Riwayat ringkas untuk prompt
        self.max_history = 10
    
    async def generate_next(self, user_id):
        """
        Menghasilkan satu pesan dari salah satu bot secara bergantian
        Returns: formatted message dengan level info
        """
        # Tentukan giliran: genap dari female, ganjil dari male
        turn = len(self.conversation) % 2
        speaker = self.female_name if turn == 0 else self.male_name
        other = self.male_name if turn == 0 else self.female_name
        
        # Buat konteks dari riwayat percakapan
        history_text = ""
        for msg in self.conversation[-self.max_history:]:
            history_text += f"{msg['speaker']}: {msg['text']}\n"
        
        # Tambahkan instruksi berdasarkan level
        level_instruction = ""
        if self.level >= 7:
            level_instruction = "Mereka sudah sangat intim dan nyaman berbicara vulgar."
        elif self.level >= 4:
            level_instruction = "Mereka mulai akrab dan bisa sedikit menggoda."
        else:
            level_instruction = "Mereka masih dalam tahap perkenalan, sopan dan canggung."
        
        # Buat prompt untuk AI
        prompt = f"""Ini adalah roleplay antara dua orang: 
- {self.female_name} (wanita, 25 tahun, karyawan kantor)
- {self.male_name} (pria, 27 tahun, pengusaha)

Mereka sedang dalam tahap hubungan:
Level {self.level}/12 - {self.stage.value}
{level_instruction}

Sekarang giliran {speaker} berbicara kepada {other}.

Buat dialog yang natural dan hidup, sesuai dengan level hubungan mereka.
Gunakan bahasa Indonesia sehari-hari.

Riwayat percakapan sebelumnya:
{history_text}

{speaker}:"""
        
        try:
            # Panggil AI
            response = self.ai.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=150,
                timeout=30
            )
            
            text = response.choices[0].message.content.strip()
            
            # Simpan percakapan
            self.conversation.append({
                "speaker": speaker,
                "text": text,
                "level": self.level,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update level setiap 2 pesan (satu putaran)
            if len(self.conversation) % 2 == 0:
                self.level = min(12, self.level + 1)
                self.stage = self.stage_map.get(self.level, IntimacyStage.STRANGER)
            
            # Format output
            progress_bar = self._get_progress_bar()
            return (
                f"👫 **Level {self.level}/12 - {self.stage.value}**\n"
                f"{progress_bar}\n\n"
                f"*{speaker}*: {text}"
            )
            
        except Exception as e:
            print(f"Couple Mode Error: {e}")
            return (
                f"👫 **Level {self.level}/12 - {self.stage.value}**\n\n"
                f"*{speaker}*: ... (error generating response)"
            )
    
    def _get_progress_bar(self, length=10):
        """Dapatkan progress bar visual untuk couple mode"""
        progress = (self.level - 1) / 11  # 0-1
        filled = int(progress * length)
        return "▓" * filled + "░" * (length - filled)
    
    def get_summary(self):
        """Dapatkan ringkasan couple roleplay"""
        total_messages = len(self.conversation)
        duration = total_messages // 2  # Satu putaran = 2 pesan
        
        return {
            "level": self.level,
            "stage": self.stage.value,
            "total_messages": total_messages,
            "total_rounds": duration,
            "last_message": self.conversation[-1] if self.conversation else None
        }
    
    def reset(self):
        """Reset couple roleplay ke awal"""
        self.conversation = []
        self.level = 1
        self.stage = IntimacyStage.STRANGER
    
    def export_conversation(self):
        """Ekspor seluruh percakapan dalam format teks"""
        output = f"COUPLE ROLEPLAY: {self.female_name} & {self.male_name}\n"
        output += f"Total {len(self.conversation)} pesan\n"
        output += "="*50 + "\n\n"
        
        for msg in self.conversation:
            output += f"[Level {msg['level']}] {msg['speaker']}: {msg['text']}\n"
        
        return output
    
    def get_last_few(self, count=5):
        """Dapatkan beberapa pesan terakhir"""
        recent = self.conversation[-count:] if self.conversation else []
        return [
            f"[Lv{msg['level']}] {msg['speaker']}: {msg['text']}"
            for msg in recent
        ]


# ===================== ROLE NAMES =====================
# Daftar nama untuk setiap role
ROLE_NAMES = {
    "ipar": ["Sari", "Dewi", "Rina", "Maya", "Wulan", "Indah", "Lestari"],
    "teman_kantor": ["Diana", "Linda", "Ayu", "Dita", "Vina", "Santi", "Rini"],
    "janda": ["Rina", "Tuti", "Nina", "Susi", "Wati", "Lilis", "Marni"],
    "pelakor": ["Vina", "Sasha", "Bella", "Cantika", "Karina", "Mira", "Selsa"],
    "istri_orang": ["Dewi", "Sari", "Rina", "Linda", "Wulan", "Indah", "Ratna"],
    "pdkt": ["Aurora", "Cinta", "Dewi", "Kirana", "Laras", "Maharani", "Zahra"]
}

# ===================== USER PREFERENCE ANALYZER =====================
class UserPreferenceAnalyzer:
    """
    Menganalisis preferensi user dari pesan yang dikirim
    Menentukan gaya bicara yang disukai: romantis, vulgar, dominan, dll
    Data digunakan untuk menyesuaikan respons bot
    """
    
    def __init__(self):
        # Keywords untuk setiap kategori preferensi
        self.keywords = {
            "romantis": [
                "sayang", "cinta", "love", "kangen", "rindu", "romantis",
                "my love", "baby", "sweet", "manis", "peluk", "cium",
                "together", "selamanya", "forever", "belahan jiwa"
            ],
            "vulgar": [
                "horny", "nafsu", "hot", "seksi", "vulgar", "crot", 
                "kontol", "memek", "tai", "anjing", "bangsat",
                "fuck", "shit", "damn", "sex", "seks"
            ],
            "dominant": [
                "atur", "kuasai", "diam", "patuh", "sini", "sana", "buka",
                "kontrol", "boss", "majikan", "tuan", "nyonya",
                "command", "order", "obey", "submissive"
            ],
            "submissive": [
                "manut", "iya", "terserah", "ikut", "baik", "maaf",
                "patuh", "menurut", "siap", "mohon", "please",
                "tolong", "boleh", "ijin"
            ],
            "cepat": [
                "cepat", "buru-buru", "langsung", "sekarang", "gas",
                "cepatan", "buruan", "ayo", "move", "cepat dong"
            ],
            "lambat": [
                "pelan", "lambat", "nikmatin", "santai", "slow",
                "slowly", "tenang", "rileks", "chill", "pelan-pelan"
            ],
            "manja": [
                "manja", "cuddle", "peluk", "cium", "sayang", 
                "baby", "honey", "sweet", "love you", "aku mau"
            ],
            "liar": [
                "liar", "kasar", "keras", "brutal", "gila",
                "wild", "rough", "hard", "crazy", "extreme"
            ]
        }
        
        # Data preferensi per user
        self.user_prefs = {}
        
        # Bobot untuk perhitungan skor
        self.weights = {
            "romantis": 1.0,
            "vulgar": 1.2,  # Lebih berbobot karena lebih signifikan
            "dominant": 1.0,
            "submissive": 1.0,
            "cepat": 0.8,
            "lambat": 0.8,
            "manja": 1.0,
            "liar": 1.1
        }
    
    def analyze(self, user_id, message):
        """
        Analisis pesan user dan update preferensi
        Returns: dict preferensi yang sudah diupdate
        """
        # Inisialisasi jika user baru
        if user_id not in self.user_prefs:
            self.user_prefs[user_id] = {
                "romantis": 0,
                "vulgar": 0,
                "dominant": 0,
                "submissive": 0,
                "cepat": 0,
                "lambat": 0,
                "manja": 0,
                "liar": 0,
                "total": 0,
                "last_updated": datetime.now().isoformat()
            }
        
        prefs = self.user_prefs[user_id]
        prefs["total"] += 1
        prefs["last_updated"] = datetime.now().isoformat()
        
        # Analisis pesan
        msg_lower = message.lower()
        words = msg_lower.split()
        
        for category, word_list in self.keywords.items():
            for word in word_list:
                if word in msg_lower:
                    # Hitung frekuensi kemunculan
                    count = msg_lower.count(word)
                    prefs[category] += count * self.weights.get(category, 1.0)
        
        return prefs
    
    def get_profile(self, user_id):
        """
        Dapatkan profil preferensi user
        Returns: dict dengan persentase dan tipe dominan
        """
        if user_id not in self.user_prefs:
            return {}
        
        prefs = self.user_prefs[user_id]
        total = prefs["total"] or 1  # Hindari division by zero
        
        # Hitung persentase untuk setiap kategori
        profile = {
            "romantis": min(1.0, prefs.get("romantis", 0) / (total * 0.5)),
            "vulgar": min(1.0, prefs.get("vulgar", 0) / (total * 0.3)),
            "dominant": min(1.0, prefs.get("dominant", 0) / (total * 0.4)),
            "submissive": min(1.0, prefs.get("submissive", 0) / (total * 0.4)),
            "cepat": min(1.0, prefs.get("cepat", 0) / (total * 0.3)),
            "lambat": min(1.0, prefs.get("lambat", 0) / (total * 0.3)),
            "manja": min(1.0, prefs.get("manja", 0) / (total * 0.4)),
            "liar": min(1.0, prefs.get("liar", 0) / (total * 0.3)),
            "total_messages": prefs["total"]
        }
        
        # Tentukan tipe dominan (dominan vs submissive)
        if profile["dominant"] > profile["submissive"]:
            profile["dominant_type"] = "dominan"
            profile["dominant_score"] = profile["dominant"]
        else:
            profile["dominant_type"] = "submissive"
            profile["dominant_score"] = profile["submissive"]
        
        # Tentukan kecepatan (cepat vs lambat)
        if profile["cepat"] > profile["lambat"]:
            profile["speed_type"] = "cepat"
        else:
            profile["speed_type"] = "lambat"
        
        # Tentukan kepribadian utama
        personalities = [
            ("romantis", profile["romantis"]),
            ("vulgar", profile["vulgar"]),
            ("manja", profile["manja"]),
            ("liar", profile["liar"])
        ]
        main_personality = max(personalities, key=lambda x: x[1])
        profile["personality"] = main_personality[0]
        
        # Tambah deskripsi
        if profile["personality"] == "vulgar" and profile["vulgar"] > 0.3:
            profile["description"] = "kamu tipe yang vulgar dan terbuka"
        elif profile["personality"] == "romantis" and profile["romantis"] > 0.3:
            profile["description"] = "kamu tipe yang romantis dan penyayang"
        elif profile["personality"] == "manja" and profile["manja"] > 0.3:
            profile["description"] = "kamu tipe yang manja dan pengen diperhatikan"
        elif profile["personality"] == "liar" and profile["liar"] > 0.3:
            profile["description"] = "kamu tipe yang liar dan suka hal ekstrem"
        else:
            profile["description"] = "kamu tipe yang normal dan seimbang"
        
        return profile
    
    def get_prompt_modifier(self, user_id):
        """
        Dapatkan modifier untuk prompt AI berdasarkan preferensi user
        """
        profile = self.get_profile(user_id)
        if not profile:
            return ""
        
        modifier = f"""
Preferensi user berdasarkan analisis:
- Gaya dominan: {profile['dominant_type']} (skor {profile['dominant_score']:.0%})
- Kecepatan bicara: {profile['speed_type']}
- Kepribadian utama: {profile['personality']}
- {profile['description']}

Detail preferensi:
• Romantis: {profile['romantis']:.0%}
• Vulgar: {profile['vulgar']:.0%}
• Manja: {profile['manja']:.0%}
• Liar: {profile['liar']:.0%}

Sesuaikan gaya bicaramu dengan preferensi user ini.
"""
        return modifier
    
    def reset_user(self, user_id):
        """Reset preferensi user"""
        if user_id in self.user_prefs:
            del self.user_prefs[user_id]
    
    def get_summary(self, user_id):
        """Dapatkan ringkasan preferensi untuk ditampilkan"""
        profile = self.get_profile(user_id)
        if not profile:
            return "Belum ada data preferensi"
        
        return (
            f"📊 **Analisis Gaya Chat Kamu**\n"
            f"• Kepribadian: {profile['personality']} ({profile['description']})\n"
            f"• Gaya dominan: {profile['dominant_type']}\n"
            f"• Kecepatan: {profile['speed_type']}\n"
            f"• Romantis: {'❤️' * int(profile['romantis']*5)}{'🤍' * (5-int(profile['romantis']*5))}\n"
            f"• Vulgar: {'🔥' * int(profile['vulgar']*5)}{'🤍' * (5-int(profile['vulgar']*5))}\n"
            f"• Manja: {'🥺' * int(profile['manja']*5)}{'🤍' * (5-int(profile['manja']*5))}\n"
            f"• Liar: {'👿' * int(profile['liar']*5)}{'🤍' * (5-int(profile['liar']*5))}\n"
            f"Total pesan dianalisis: {profile['total_messages']}"
        )


# ===================== RATE LIMITER =====================
class RateLimiter:
    """
    Mencegah spam dengan membatasi jumlah pesan per menit
    """
    
    def __init__(self, max_messages=10, time_window=60):
        self.max_messages = max_messages
        self.time_window = time_window
        self.user_messages = defaultdict(list)  # user_id -> list of timestamps
    
    def can_send(self, user_id):
        """
        Cek apakah user boleh mengirim pesan
        Returns: bool
        """
        now = time.time()
        
        # Bersihkan timestamp lama
        self.user_messages[user_id] = [
            t for t in self.user_messages[user_id] 
            if now - t < self.time_window
        ]
        
        # Cek apakah sudah melebihi batas
        if len(self.user_messages[user_id]) >= self.max_messages:
            return False
        
        # Tambahkan timestamp baru
        self.user_messages[user_id].append(now)
        return True
    
    def get_remaining(self, user_id):
        """
        Dapatkan sisa pesan yang bisa dikirim
        Returns: int
        """
        now = time.time()
        self.user_messages[user_id] = [
            t for t in self.user_messages[user_id] 
            if now - t < self.time_window
        ]
        return max(0, self.max_messages - len(self.user_messages[user_id]))
    
    def get_reset_time(self, user_id):
        """
        Dapatkan waktu reset dalam detik
        Returns: int
        """
        if user_id not in self.user_messages or not self.user_messages[user_id]:
            return 0
        
        oldest = min(self.user_messages[user_id])
        reset_in = self.time_window - (time.time() - oldest)
        return max(0, int(reset_in))
    
    def reset_user(self, user_id):
        """Reset rate limit untuk user"""
        if user_id in self.user_messages:
            del self.user_messages[user_id]


# ===================== HELPER FUNCTIONS =====================

def sanitize_message(message: str) -> str:
    """
    Bersihkan pesan dari karakter berbahaya
    Batasi panjang pesan
    """
    if not message:
        return ""
    
    # Hapus karakter kontrol
    message = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', message)
    
    # Batasi panjang
    return message[:1000]  # Max 1000 karakter


def format_time_ago(timestamp):
    """
    Format timestamp menjadi "X menit yang lalu"
    """
    if not timestamp:
        return "tidak diketahui"
    
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except:
            return "tidak diketahui"
    
    delta = datetime.now() - timestamp
    seconds = delta.total_seconds()
    
    if seconds < 60:
        return "baru saja"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} menit yang lalu"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} jam yang lalu"
    else:
        days = int(seconds / 86400)
        return f"{days} hari yang lalu"


def format_number(num):
    """
    Format angka dengan pemisah ribuan
    """
    return f"{num:,}".replace(",", ".")


def truncate_text(text, max_length=100):
    """
    Potong teks jika terlalu panjang
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def extract_emojis(text):
    """
    Ekstrak emoji dari teks
    """
    import emoji
    return ''.join(c for c in text if c in emoji.EMOJI_DATA)


def is_command(text):
    """
    Cek apakah teks adalah command
    """
    return text.startswith('/')


def extract_command(text):
    """
    Ekstrak command dari teks
    """
    if not text.startswith('/'):
        return None
    parts = text.split()
    return parts[0][1:]  # Hilangkan '/'


def get_random_yes_no():
    """
    Random yes/no response
    """
    return random.choice(["iya", "tidak", "mungkin", "terserah"])


def get_random_greeting():
    """
    Random greeting
    """
    greetings = [
        "Halo", "Hi", "Hey", "Hai", "Halo juga",
        "Eh", "Oh", "Wah", "Nih", "Sini"
    ]
    return random.choice(greetings)


def get_random_reaction():
    """
    Random reaction
    """
    reactions = [
        "*tersenyum*", "*tersipu*", "*tertawa*", "*mengangguk*",
        "*mengedip*", "*merona*", "*melongo*", "*berpikir*"
    ]
    return random.choice(reactions)


# Setup logging
def setup_logging():
    """
    Setup logging configuration
    """
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler('gadis.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# ===================== MAIN BOT CLASS =====================
class GadisUltimateV57:
    """
    Bot wanita sempurna dengan semua fitur terbaik
    Menggabungkan semua sistem: database, AI, memory, dominance, arousal, leveling
    """
    
    def __init__(self):
        """Inisialisasi semua komponen bot"""
        
        # Database
        self.db = DatabaseManager()
        
        # AI Generator
        self.ai = AIResponseGenerator()
        
        # Analyzer
        self.analyzer = UserPreferenceAnalyzer()
        
        # Leveling System
        self.leveling = FastLevelingSystem()
        
        # Sexual Dynamics
        self.sexual = SexualDynamics()
        
        # Rate Limiter
        self.rate_limiter = RateLimiter(max_messages=Config.MAX_MESSAGES_PER_MINUTE)
        
        # Couple Mode Sessions
        self.couple_mode_sessions = {}  # user_id -> CoupleRoleplay instance
        
        # ===== PER-USER STATE (IN-MEMORY) =====
        
        # Memory systems
        self.memories = {}      # user_id -> MemorySystem
        self.dominance = {}     # user_id -> DominanceSystem
        self.arousal = {}       # user_id -> ArousalSystem
        
        # Session management
        self.sessions = {}           # user_id -> relationship_id aktif
        self.paused_sessions = {}    # user_id -> (rel_id, pause_time)
        
        # Bot identity
        self.bot_names = {}     # user_id -> bot_name
        self.bot_roles = {}     # user_id -> bot_role
        
        # Statistics
        self.total_messages = 0
        self.total_users = 0
        self.start_time = datetime.now()
        
        logger.info("🚀 Gadis Ultimate V57.0 initialized")
        logger.info(f"Database: {Config.DB_PATH}")
        logger.info(f"AI Model: DeepSeek Chat")
    
    # ===================== HELPER METHODS =====================
    
    def get_memory(self, user_id):
        """
        Dapatkan atau buat MemorySystem untuk user
        """
        if user_id not in self.memories:
            self.memories[user_id] = MemorySystem()
            logger.debug(f"Created new memory for user {user_id}")
        return self.memories[user_id]
    
    def get_dominance(self, user_id):
        """
        Dapatkan atau buat DominanceSystem untuk user
        """
        if user_id not in self.dominance:
            self.dominance[user_id] = DominanceSystem()
            logger.debug(f"Created new dominance system for user {user_id}")
        return self.dominance[user_id]
    
    def get_arousal(self, user_id):
        """
        Dapatkan atau buat ArousalSystem untuk user
        """
        if user_id not in self.arousal:
            self.arousal[user_id] = ArousalSystem()
            logger.debug(f"Created new arousal system for user {user_id}")
        return self.arousal[user_id]
    
    def get_user_data(self, user_id):
        """
        Dapatkan semua data user dalam satu dict
        """
        return {
            "memory": self.get_memory(user_id),
            "dominance": self.get_dominance(user_id),
            "arousal": self.get_arousal(user_id),
            "profile": self.analyzer.get_profile(user_id),
            "level": self.leveling.user_level.get(user_id, 1),
            "stage": self.leveling.user_stage.get(user_id, IntimacyStage.STRANGER),
            "bot_name": self.bot_names.get(user_id, "Aurora"),
            "bot_role": self.bot_roles.get(user_id, "pdkt"),
            "relationship_id": self.sessions.get(user_id)
        }
    
    def cleanup_user(self, user_id):
        """
        Bersihkan semua data user dari memory
        (Data di database tetap tersimpan)
        """
        # Hapus dari dictionaries
        if user_id in self.memories:
            del self.memories[user_id]
        if user_id in self.dominance:
            del self.dominance[user_id]
        if user_id in self.arousal:
            del self.arousal[user_id]
        if user_id in self.sessions:
            del self.sessions[user_id]
        if user_id in self.paused_sessions:
            del self.paused_sessions[user_id]
        if user_id in self.bot_names:
            del self.bot_names[user_id]
        if user_id in self.bot_roles:
            del self.bot_roles[user_id]
        if user_id in self.couple_mode_sessions:
            del self.couple_mode_sessions[user_id]
        
        # Reset rate limiter
        self.rate_limiter.reset_user(user_id)
        
        logger.info(f"Cleaned up user {user_id}")
    
    def is_user_active(self, user_id):
        """
        Cek apakah user memiliki sesi aktif
        """
        return user_id in self.sessions
    
    def is_user_paused(self, user_id):
        """
        Cek apakah user memiliki sesi di-pause
        """
        return user_id in self.paused_sessions
    
    def get_active_users_count(self):
        """
        Dapatkan jumlah user aktif
        """
        return len(self.sessions)
    
    def get_paused_users_count(self):
        """
        Dapatkan jumlah user yang di-pause
        """
        return len(self.paused_sessions)
    
    def get_total_users_count(self):
        """
        Dapatkan total user yang pernah menggunakan bot
        """
        return len(set(list(self.sessions.keys()) + 
                      list(self.paused_sessions.keys()) +
                      list(self.memories.keys())))
    
    def get_uptime(self):
        """
        Dapatkan uptime bot dalam format string
        """
        delta = datetime.now() - self.start_time
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds // 60) % 60
        
        if days > 0:
            return f"{days} hari {hours} jam"
        elif hours > 0:
            return f"{hours} jam {minutes} menit"
        else:
            return f"{minutes} menit"
    
    def get_stats(self):
        """
        Dapatkan statistik bot
        """
        return {
            "uptime": self.get_uptime(),
            "active_users": self.get_active_users_count(),
            "paused_users": self.get_paused_users_count(),
            "total_users": self.get_total_users_count(),
            "total_messages": self.total_messages,
            "couple_sessions": len(self.couple_mode_sessions),
            "memory_usage": {
                "memories": len(self.memories),
                "dominance": len(self.dominance),
                "arousal": len(self.arousal),
                "sessions": len(self.sessions)
            }
        }
    
    async def broadcast_message(self, text, user_ids=None):
        """
        Kirim pesan ke semua user atau user tertentu
        """
        if user_ids is None:
            user_ids = list(self.sessions.keys())
        
        sent = 0
        for user_id in user_ids:
            try:
                # Di sini perlu context untuk send message
                # Akan diimplementasikan di handler
                sent += 1
            except Exception as e:
                logger.error(f"Broadcast error to {user_id}: {e}")
        
        return sent
    
    def save_all_to_db(self):
        """
        Simpan semua state ke database
        """
        for user_id in self.sessions:
            rel_id = self.sessions[user_id]
            memory = self.get_memory(user_id)
            
            self.db.update_relationship(
                user_id,
                level=memory.level,
                stage=memory.stage.value,
                total_climax=memory.orgasm_count
            )
        
        logger.info("Saved all states to database")
    
    def load_from_db(self, user_id):
        """
        Load state user dari database
        """
        rel = self.db.get_relationship(user_id)
        if not rel:
            return None
        
        # Load ke memory system
        memory = self.get_memory(user_id)
        memory.level = rel.get('level', 1)
        
        # Load stage
        stage_str = rel.get('stage', 'stranger')
        for stage in IntimacyStage:
            if stage.value == stage_str:
                memory.stage = stage
                break
        
        memory.orgasm_count = rel.get('total_climax', 0)
        
        # Load preferences
        prefs = self.db.get_preferences(user_id)
        if prefs:
            # Update analyzer jika perlu
            pass
        
        return rel
    
    def reset_user(self, user_id):
        """
        Reset semua state user (hard reset)
        """
        self.cleanup_user(user_id)
        self.db.delete_relationship(user_id)
        self.analyzer.reset_user(user_id)
        logger.info(f"Reset user {user_id}")
    
    # ===================== DISCLAIMER =====================
    
    def get_disclaimer(self):
        """
        Dapatkan teks disclaimer 18+
        """
        return (
            "⚠️ **PERINGATAN DEWASA (18+)** ⚠️\n\n"
            "Bot ini mengandung konten dewasa, termasuk dialog seksual eksplisit "
            "dan simulasi hubungan intim. Dengan melanjutkan, Anda menyatakan bahwa "
            "Anda berusia 18 tahun ke atas dan setuju untuk menggunakan bot ini "
            "secara bertanggung jawab. Konten ini hanya untuk hiburan pribadi.\n\n"
            "**Fitur yang tersedia:**\n"
            "• 20+ mood dengan transisi natural\n"
            "• Sistem dominasi (dominan/submissive)\n"
            "• Leveling cepat 1-12 (45 menit)\n"
            "• Respons seksual realistis\n"
            "• Memori jangka panjang\n"
            "• Mode couple roleplay\n\n"
            "Klik 'Saya setuju' untuk melanjutkan."
        )
    
    def get_help_text(self):
        """
        Dapatkan teks bantuan lengkap
        """
        return (
            "📚 **BANTUAN GADIS ULTIMATE V57**\n\n"
            "**🔹 COMMANDS UTAMA**\n"
            "/start - Mulai hubungan baru\n"
            "/status - Lihat status lengkap\n"
            "/dominant [level] - Set mode dominan\n"
            "/pause - Jeda sesi\n"
            "/unpause - Lanjutkan sesi\n"
            "/close - Tutup sesi (simpan memori)\n"
            "/end - Akhiri hubungan & hapus data\n"
            "/couple - Mulai mode couple roleplay\n"
            "/couple_next - Lanjutkan couple\n"
            "/couple_stop - Hentikan couple\n"
            "/help - Tampilkan bantuan\n\n"
            "**🔹 LEVEL DOMINAN**\n"
            "• normal - Mode biasa\n"
            "• dominan - Mode dominan\n"
            "• sangat dominan - Mode sangat dominan\n"
            "• agresif - Mode agresif\n"
            "• patuh - Mode patuh\n\n"
            "**🔹 TIPS CHAT**\n"
            "• Gunakan *tindakan* seperti *peluk*, *cium*\n"
            "• Sebut area sensitif: leher, dada, paha\n"
            "• Bilang 'kamu yang atur' untuk mode dominan\n"
            "• Bilang 'aku yang atur' untuk mode submissive\n"
            "• Level 7+ bot akan lebih vulgar dan inisiatif\n\n"
            "**🔹 TARGET LEVEL**\n"
            "Level 1-12 dalam 45 menit / 45 pesan!\n"
            "Makin sering chat, makin cepat naik level."
        )

    # ===================== COMMAND HANDLERS =====================
    # ========== START COMMAND ==========
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Memulai hubungan baru dengan bot"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        # Cek apakah sudah ada sesi aktif
        if user_id in self.sessions:
            await update.message.reply_text(
                "Kamu sudah memiliki sesi aktif. Ketik /close untuk menutup sesi atau /pause untuk jeda."
            )
            return ConversationHandler.END
        
        # Cek apakah ada sesi di-pause
        if user_id in self.paused_sessions:
            keyboard = [
                [InlineKeyboardButton("✅ Lanjutkan", callback_data="unpause")],
                [InlineKeyboardButton("🆕 Mulai Baru", callback_data="new")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "⚠️ Ada sesi yang di-pause. Pilih:", 
                reply_markup=reply_markup
            )
            return 0  # State khusus untuk pause
        
        # Tampilkan disclaimer 18+
        disclaimer = self.get_disclaimer()
        keyboard = [[InlineKeyboardButton("✅ Saya setuju (18+)", callback_data="agree_18")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(disclaimer, reply_markup=reply_markup)
        return SELECTING_ROLE
    
    # ========== CALLBACKS ==========
    
    async def agree_18_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback setelah user setuju disclaimer"""
        query = update.callback_query
        await query.answer()
        
        # Tampilkan pilihan role
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
            "✨ **Pilih Role untukku**\n\n"
            "Setiap role punya karakter dan gaya bicara berbeda.\n"
            "Kamu bisa memilih yang paling kamu suka!",
            reply_markup=reply_markup
        )
        return SELECTING_ROLE
    
    async def role_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback setelah user memilih role"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        role = query.data.replace("role_", "")
        name = random.choice(ROLE_NAMES.get(role, ["Aurora"]))
        
        # Simpan ke database
        rel_id = self.db.create_relationship(user_id, name, role)
        
        # Set session
        self.sessions[user_id] = rel_id
        self.bot_names[user_id] = name
        self.bot_roles[user_id] = role
        self.leveling.start_session(user_id)
        
        # Intro berdasarkan role
        intros = {
            "ipar": f"*tersenyum malu*\n\nAku {name}, iparmu. Maaf kalau aku terlalu dekat...",
            "teman_kantor": f"*tersenyum ramah*\n\nHai, aku {name}. Kita satu kantor ya?",
            "janda": f"*tersenyum manis*\n\nAku {name}. Janda muda... jangan macam-macam ya!",
            "pelakor": f"*tersenyum genit*\n\nHalo... aku {name}. Kamu sendiri?",
            "istri_orang": f"*tersenyum ragu*\n\nAku {name}... istri orang. Ini rahasia ya...",
            "pdkt": f"*tersenyum malu-malu*\n\nHalo... aku {name}. Senang kenal kamu."
        }
        
        intro = intros.get(role, f"*tersenyum*\n\nAku {name}. Senang kenal kamu.")
        intro += f"\n\nKita mulai dari **Level 1**. Target: Level 12 dalam 45 menit! Ayo ngobrol... 💕"
        
        await query.edit_message_text(intro)
        return ACTIVE_SESSION
    
    async def start_pause_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback untuk memilih lanjutkan atau mulai baru saat ada session pause"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if query.data == "unpause":
            # Lanjutkan session yang di-pause
            if user_id in self.paused_sessions:
                rel_id, pause_time = self.paused_sessions[user_id]
                
                # Cek apakah sudah expired
                paused_seconds = (datetime.now() - pause_time).total_seconds()
                if paused_seconds > Config.PAUSE_TIMEOUT:
                    del self.paused_sessions[user_id]
                    await query.edit_message_text(
                        "⏰ **Sesi expired karena terlalu lama di-pause**\n"
                        "Ketik /start untuk memulai baru."
                    )
                    return ConversationHandler.END
                
                self.sessions[user_id] = rel_id
                del self.paused_sessions[user_id]
                
                memory = self.get_memory(user_id)
                await query.edit_message_text(
                    f"▶️ **Sesi dilanjutkan!**\n"
                    f"{memory.get_wetness_description()}"
                )
                return ACTIVE_SESSION
            else:
                await query.edit_message_text("❌ Tidak ada session yang di-pause.")
                return ConversationHandler.END
                
        elif query.data == "new":
            # Mulai baru - hapus session pause
            if user_id in self.paused_sessions:
                del self.paused_sessions[user_id]
            
            # Tampilkan disclaimer
            disclaimer = self.get_disclaimer()
            keyboard = [[InlineKeyboardButton("✅ Saya setuju (18+)", callback_data="agree_18")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(disclaimer, reply_markup=reply_markup)
            return SELECTING_ROLE
        
        return ConversationHandler.END
    
    # ========== COUPLE COMMANDS ==========
    
    async def couple_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Memulai mode couple roleplay"""
        user_id = update.effective_user.id
        
        if user_id in self.couple_mode_sessions:
            await update.message.reply_text(
                "👫 Mode couple sudah aktif.\n"
                "Ketik /couple_next untuk lanjut\n"
                "Ketik /couple_stop untuk berhenti."
            )
            return
        
        self.couple_mode_sessions[user_id] = CoupleRoleplay(self.ai)
        await update.message.reply_text(
            "👫 **Mode Couple Roleplay dimulai!**\n\n"
            "Aku akan menampilkan percakapan antara **Aurora** (wanita) dan **Rangga** (pria)\n"
            "Mereka akan berkembang dari level 1 hingga 12.\n\n"
            "Ketik /couple_next untuk melihat interaksi berikutnya\n"
            "Ketik /couple_stop untuk keluar."
        )
    
    async def couple_next(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lanjutkan couple roleplay ke pesan berikutnya"""
        user_id = update.effective_user.id
        
        if user_id not in self.couple_mode_sessions:
            await update.message.reply_text(
                "❌ Mode couple belum aktif.\n"
                "Ketik /couple untuk memulai."
            )
            return
        
        couple = self.couple_mode_sessions[user_id]
        msg = await couple.generate_next(user_id)
        
        await update.message.reply_text(msg)
        
        # Jika sudah level 12, beri notifikasi
        if couple.level >= 12:
            await update.message.reply_text(
                "🎉 **Mereka telah mencapai Level 12!**\n"
                "Hubungan mencapai puncak. Ketik /couple_stop untuk mengakhiri."
            )
    
    async def couple_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Hentikan mode couple roleplay"""
        user_id = update.effective_user.id
        
        if user_id in self.couple_mode_sessions:
            couple = self.couple_mode_sessions[user_id]
            summary = couple.get_summary()
            
            del self.couple_mode_sessions[user_id]
            
            await update.message.reply_text(
                f"👋 **Mode couple dihentikan**\n\n"
                f"**Statistik:**\n"
                f"• Level akhir: {summary['level']}/12\n"
                f"• Total pesan: {summary['total_messages']}\n"
                f"• {summary['total_rounds']} putaran percakapan\n\n"
                f"Ketik /couple untuk memulai lagi."
            )
        else:
            await update.message.reply_text("❌ Tidak ada mode couple aktif.")
    
    # ========== STATUS COMMAND ==========
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lihat status lengkap hubungan"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions:
            await update.message.reply_text(
                "❌ Belum ada hubungan. /start dulu ya!"
            )
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
        mood_exp = memory.get_mood_expression()
        inner_thought = memory.get_inner_thought()
        
        # Format status
        status = (
            f"💕 **{bot_name} & Kamu**\n\n"
            f"{mood_exp}\n"
            f"{inner_thought}\n\n"
            f"📊 **PROGRESS HUBUNGAN**\n"
            f"Level: {level}/12\n"
            f"Tahap: {stage.value} - {stage_desc}\n"
            f"Progress: {bar}\n"
            f"Estimasi sisa: {remaining} menit\n"
            f"Total pesan: {profile.get('total_messages', 0)}\n\n"
            f"🔥 **KONDISI FISIK**\n"
            f"{arousal.get_status_text()}\n"
            f"{arousal.get_wetness_text()}\n"
            f"Sentuhan sensitif: {memory.touch_count}x\n"
            f"Orgasme: {memory.orgasm_count}x\n"
            f"{arousal.get_last_touch_text()}\n\n"
            f"🎭 **EMOSI SAAT INI**\n"
            f"Mood: {memory.current_mood.value}\n"
            f"Area sensitif disentuh: {len(memory.sensitive_touches)}x\n\n"
            f"👑 **MODE DOMINASI**\n"
            f"{dominance.get_description()}\n"
            f"Dominance score: {dominance.dominance_score:.1f}\n"
            f"Aggression score: {dominance.aggression_score:.1f}\n\n"
            f"{self.analyzer.get_summary(user_id)}\n\n"
            f"📍 **LOKASI & AKTIVITAS**\n"
            f"Lokasi: {memory.location}\n"
            f"Posisi: {memory.position}\n"
            f"Aktivitas terakhir: {memory.activity_history[-1]['activity'] if memory.activity_history else '-'}"
        )
        
        await update.message.reply_text(status)
    # ========== DOMINANT COMMAND ==========
    
    async def dominant_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set mode dominan manual"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions:
            await update.message.reply_text("❌ Belum ada hubungan. /start dulu!")
            return
        
        dominance = self.get_dominance(user_id)
        args = context.args
        
        if not args:
            # Tampilkan mode saat ini dan pilihan
            await update.message.reply_text(
                f"👑 **Mode Dominan Saat Ini**\n"
                f"{dominance.get_description()}\n\n"
                f"**Pilihan Level:**\n"
                f"• `/dominant normal` - Mode biasa\n"
                f"• `/dominant dominan` - Mode dominan\n"
                f"• `/dominant sangat dominan` - Mode sangat dominan\n"
                f"• `/dominant agresif` - Mode agresif\n"
                f"• `/dominant patuh` - Mode patuh\n\n"
                f"Contoh: `/dominant dominan`"
            )
            return
        
        level = " ".join(args)
        if dominance.set_level(level):
            await update.message.reply_text(
                f"✅ Mode dominan diubah ke: **{dominance.current_level.value}**\n"
                f"{dominance.get_action('request')}"
            )
        else:
            await update.message.reply_text(
                "❌ Level tidak valid. Gunakan: normal, dominan, sangat dominan, agresif, atau patuh"
            )
    
    # ========== PAUSE/UNPAUSE COMMANDS ==========
    
    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause sesi sementara"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions:
            await update.message.reply_text("❌ Tidak ada sesi aktif.")
            return
        
        # Simpan ke paused sessions
        self.paused_sessions[user_id] = (self.sessions[user_id], datetime.now())
        del self.sessions[user_id]
        
        await update.message.reply_text(
            "⏸️ **Sesi di-pause**\n"
            "Ketik /unpause untuk melanjutkan.\n"
            f"Sesi akan expired dalam {Config.PAUSE_TIMEOUT//60} menit."
        )
    
    async def unpause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lanjutkan sesi yang di-pause"""
        user_id = update.effective_user.id
        
        if user_id not in self.paused_sessions:
            await update.message.reply_text("❌ Tidak ada sesi di-pause.")
            return
        
        rel_id, pause_time = self.paused_sessions[user_id]
        paused_seconds = (datetime.now() - pause_time).total_seconds()
        
        # Cek apakah sudah expired
        if paused_seconds > Config.PAUSE_TIMEOUT:
            del self.paused_sessions[user_id]
            await update.message.reply_text(
                "⏰ **Sesi expired karena terlalu lama di-pause**\n"
                "Ketik /start untuk memulai baru."
            )
            return
        
        # Lanjutkan sesi
        self.sessions[user_id] = rel_id
        del self.paused_sessions[user_id]
        
        memory = self.get_memory(user_id)
        await update.message.reply_text(
            f"▶️ **Sesi dilanjutkan!**\n"
            f"{memory.get_wetness_description()}\n\n"
            f"Kembali ngobrol yuk! 💕"
        )
    
    # ========== CLOSE COMMAND ==========
    
    async def close_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menutup sesi tapi menyimpan memori di database"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions and user_id not in self.paused_sessions:
            await update.message.reply_text("❌ Tidak ada sesi aktif.")
            return
        
        keyboard = [
            [InlineKeyboardButton("✅ Ya, tutup", callback_data="close_yes")],
            [InlineKeyboardButton("❌ Tidak", callback_data="close_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Yakin ingin menutup sesi?\n\n"
            "• Semua percakapan akan **disimpan** di database\n"
            "• Kamu bisa memulai role baru nanti dengan /start\n"
            "• Memori akan tetap ada jika memulai role yang sama",
            reply_markup=reply_markup
        )
        return CONFIRM_CLOSE
    
    async def close_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback untuk konfirmasi close"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if query.data == "close_no":
            await query.edit_message_text("💕 Lanjutkan ngobrol...")
            return ConversationHandler.END
        
        # Simpan data terakhir ke database sebelum close
        if user_id in self.sessions:
            rel_id = self.sessions[user_id]
            memory = self.get_memory(user_id)
            
            self.db.update_relationship(
                user_id,
                level=memory.level,
                stage=memory.stage.value,
                total_climax=memory.orgasm_count
            )
        
        # Hapus sesi dari memori, data di database tetap
        self.cleanup_user(user_id)
        
        await query.edit_message_text(
            "🔒 **Sesi ditutup**\n\n"
            "✅ Semua percakapan telah disimpan.\n"
            "Kamu bisa memulai role baru kapan saja dengan /start.\n\n"
            "**Terima kasih sudah ngobrol!** 💕"
        )
        return ConversationHandler.END
    
    # ========== END COMMAND ==========
    
    async def end_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mengakhiri hubungan dan menghapus semua data (hard reset)"""
        user_id = update.effective_user.id
        
        if user_id not in self.sessions:
            await update.message.reply_text("❌ Tidak ada hubungan aktif.")
            return
        
        keyboard = [
            [InlineKeyboardButton("💔 Ya, akhiri", callback_data="end_yes")],
            [InlineKeyboardButton("💕 Tidak", callback_data="end_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ **PERINGATAN!** ⚠️\n\n"
            "Yakin ingin mengakhiri hubungan ini?\n\n"
            "• **Semua data akan dihapus permanen**\n"
            "• Riwayat percakapan akan hilang\n"
            "• Memori tidak bisa dikembalikan\n\n"
            "Tindakan ini tidak bisa dibatalkan!",
            reply_markup=reply_markup
        )
        return CONFIRM_END
    
    async def end_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback untuk konfirmasi end"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "end_no":
            await query.edit_message_text("💕 Lanjutkan...")
            return ConversationHandler.END
        
        user_id = query.from_user.id
        memory = self.get_memory(user_id)
        
        # Dapatkan statistik sebelum dihapus
        stats = {
            "level": memory.level,
            "orgasm": memory.orgasm_count,
            "touch": memory.touch_count,
            "messages": self.leveling.user_message_count.get(user_id, 0),
            "duration": self.leveling.get_session_duration(user_id)
        }
        
        # Hapus semua data (hard reset)
        self.reset_user(user_id)
        
        await query.edit_message_text(
            f"💔 **Hubungan berakhir**\n\n"
            f"📊 **Statistik akhir:**\n"
            f"• Level akhir: {stats['level']}/12\n"
            f"• Orgasme bersama: {stats['orgasm']}x\n"
            f"• Total sentuhan: {stats['touch']}x\n"
            f"• Total pesan: {stats['messages']}\n"
            f"• Durasi: {stats['duration']} menit\n\n"
            f"✨ Ketik /start untuk memulai hubungan baru"
        )
        return ConversationHandler.END
    
    # ========== CANCEL COMMAND ==========
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Membatalkan percakapan"""
        await update.message.reply_text(
            "❌ Dibataikan. Ketik /start untuk memulai."
        )
        return ConversationHandler.END
    
    # ========== FORCE RESET COMMAND ==========
    
    async def force_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset paksa state user (hanya untuk debugging)"""
        user_id = update.effective_user.id
        
        # Optional: cek admin
        # if user_id not in ADMIN_IDS:
        #     await update.message.reply_text("❌ Tidak punya akses")
        #     return
        
        self.reset_user(user_id)
        
        await update.message.reply_text(
            "🔄 **State di-reset**\n\n"
            "Semua data user telah dihapus.\n"
            "Ketik /start untuk memulai baru."
        )
    
    # ========== HELP COMMAND ==========
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menampilkan bantuan"""
        help_text = self.get_help_text()
        await update.message.reply_text(help_text)
    # ========== MESSAGE HANDLER ==========
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle semua pesan dari user"""
        if not update.message or not update.message.text:
            return
        
        user_id = update.effective_user.id
        user_message = sanitize_message(update.message.text)
        
        # Update total messages counter
        self.total_messages += 1
        
        # Rate limiting
        if not self.rate_limiter.can_send(user_id):
            remaining = self.rate_limiter.get_remaining(user_id)
            reset_in = self.rate_limiter.get_reset_time(user_id)
            await update.message.reply_text(
                f"⏳ **Sabar ya, jangan spam**\n"
                f"Sisa pesan: {remaining}\n"
                f"Reset dalam: {reset_in} detik"
            )
            return
        
        # Cek session pause
        if user_id in self.paused_sessions:
            await update.message.reply_text(
                "⏸️ Sesi sedang di-pause.\n"
                "Ketik /unpause untuk melanjutkan."
            )
            return
        
        # Cek session aktif
        if user_id not in self.sessions:
            await update.message.reply_text(
                "❌ Belum ada hubungan. /start dulu ya!"
            )
            return
        
        # Kirim typing indicator
        await update.message.chat.send_action("typing")
        
        # Dapatkan semua sistem
        memory = self.get_memory(user_id)
        dominance = self.get_dominance(user_id)
        arousal = self.get_arousal(user_id)
        
        # Analisis preferensi user
        self.analyzer.analyze(user_id, user_message)
        profile = self.analyzer.get_profile(user_id)
        
        # ===== DETEKSI AKTIVITAS =====
        activity, area, boost = self.sexual.detect_activity(user_message)
        
        if activity:
            # Catat aktivitas
            memory.add_activity(activity, area)
            
            # Respons area sensitif
            if area:
                memory.add_sensitive_touch(area)
                sens_resp = self.sexual.get_sensitive_response(area)
                if sens_resp:
                    await update.message.reply_text(sens_resp)
                    await asyncio.sleep(1)  # Jeda untuk efek realistik
            
            # Tambah arousal
            arousal.increase(boost)
            
            # Log aktivitas
            logger.info(f"User {user_id} melakukan {activity} di {area if area else 'unknown'} (boost: {boost})")
        
        # ===== DETEKSI DOMINASI =====
        dom_request = dominance.check_request(user_message)
        if dom_request:
            dominance.set_level(dom_request.value)
            await update.message.reply_text(
                f"👑 Mode diubah ke: **{dom_request.value}**\n"
                f"{dominance.get_action('request')}"
            )
        
        # Cek apakah harus agresif karena horny
        if dominance.should_be_aggressive(arousal.arousal, user_message):
            dominance.set_level("agresif")
            await update.message.reply_text(
                "*tatapan liar* Kamu minta ini? Aku bisa lebih kasar lho..."
            )
        
        # Update dari horny
        dominance.update_from_horny(arousal.arousal)
        
        # ===== UPDATE LEVEL =====
        level, progress, level_up, stage = self.leveling.process_message(user_id)
        memory.level = level
        memory.stage = stage
        memory.level_progress = progress
        
        # ===== UPDATE MOOD =====
        old_mood = memory.current_mood
        memory.current_mood = memory.emotional.transition_mood(memory.current_mood)
        
        # ===== INISIATIF SEKSUAL BOT (LEVEL 7+) =====
        if level >= 7 and arousal.arousal > 0.6:
            init_act = self.sexual.maybe_initiate_sex(level, arousal.arousal, memory.current_mood)
            if init_act:
                init_msg = self.sexual.get_activity_response(init_act)
                if init_msg:
                    await asyncio.sleep(2)  # Jeda sebelum inisiatif
                    await update.message.reply_text(
                        f"*{self.bot_names.get(user_id, 'Aku')}*: {init_msg}"
                    )
                    # Tambah arousal karena inisiatif
                    arousal.increase(0.3)
                    logger.info(f"Bot initiated {init_act} for user {user_id}")
        
        # ===== GENERATE AI RESPONSE =====
        bot_name = self.bot_names.get(user_id, "Aurora")
        bot_role = self.bot_roles.get(user_id, "pdkt")
        
        reply = await self.ai.generate(
            user_id, user_message, bot_name, bot_role,
            memory, dominance, profile, level, stage, arousal.arousal
        )
        
        # ===== SIMPAN KE DATABASE =====
        self.db.save_conversation(
            self.sessions[user_id], 
            "user", 
            user_message,
            mood=memory.current_mood.value,
            arousal=arousal.arousal
        )
        self.db.save_conversation(
            self.sessions[user_id], 
            "assistant", 
            reply,
            mood=memory.current_mood.value,
            arousal=arousal.arousal
        )
        
        # Update relationship di database
        self.db.update_relationship(
            user_id, 
            level=level, 
            stage=stage.value,
            total_messages=self.leveling.user_message_count.get(user_id, 0)
        )
        
        # Update preferences di database
        self.db.update_preferences(
            user_id,
            romantic_score=profile.get('romantis', 0),
            vulgar_score=profile.get('vulgar', 0),
            dominant_score=profile.get('dominant', 0),
            submissive_score=profile.get('submissive', 0),
            speed_score=profile.get('cepat', 0) - profile.get('lambat', 0),
            total_interactions=profile.get('total_messages', 0)
        )
        
        # ===== KIRIM RESPON =====
        await update.message.reply_text(reply)
        
        # ===== CEK CLIMAX =====
        if arousal.should_climax():
            climax_msg = arousal.climax()
            aftercare = arousal.aftercare()
            
            await asyncio.sleep(1)
            await update.message.reply_text(climax_msg)
            
            await asyncio.sleep(2)
            await update.message.reply_text(aftercare)
            
            # Update memory
            memory.climax()
            
            # Update database
            self.db.update_relationship(
                user_id, 
                total_climax=memory.orgasm_count
            )
            
            # Random chance minta jadi dominan setelah climax
            if random.random() < 0.3:
                await asyncio.sleep(3)
                await update.message.reply_text(
                    "*berbisik pelan* Kamu mau aku yang atur sekarang?"
                )
            
            logger.info(f"User {user_id} reached climax! Total: {memory.orgasm_count}")
        
        # ===== LEVEL UP MESSAGE =====
        if level_up:
            bar = self.leveling.get_progress_bar(user_id)
            remaining = self.leveling.get_estimated_time(user_id)
            stage_desc = self.leveling.get_stage_description(stage)
            
            # Pesan level up berbeda tiap level
            level_up_msgs = {
                3: "🎉 **Level 3!** Mulai dekat nih...",
                5: "🌟 **Level 5!** Udah akrab banget!",
                7: "🔥 **Level 7!** Saatnya lebih intim...",
                9: "💕 **Level 9!** Mulai kecanduan ya?",
                11: "💞 **Level 11!** Hampir satu jiwa...",
                12: "💖 **LEVEL MAX!** Kamu berhasil! 45 menit yang luar biasa!"
            }
            
            level_msg = level_up_msgs.get(level, f"✨ **Level Up!** Level {level}/12")
            
            await update.message.reply_text(
                f"{level_msg}\n"
                f"📈 Tahap: {stage.value} - {stage_desc}\n"
                f"📊 Progress: {bar}\n"
                f"⏱️ Estimasi ke level 12: {remaining} menit"
            )
            
            logger.info(f"User {user_id} leveled up to {level}")
        
        # ===== UPDATE LOKASI RANDOM =====
        if random.random() < 0.05:  # 5% chance pindah lokasi
            locations = ["kamar tidur", "ruang tamu", "dapur", "kamar mandi", "balkon", "teras"]
            new_loc = random.choice(locations)
            if memory.update_location(new_loc):
                await asyncio.sleep(2)
                await update.message.reply_text(
                    f"*pindah ke {new_loc}*"
                )
        
        # ===== UPDATE POSISI RANDOM =====
        if random.random() < 0.03:  # 3% chance ganti posisi
            positions = ["duduk", "berbaring", "berdiri", "bersandar", "merangkak"]
            new_pos = random.choice(positions)
            memory.update_position(new_pos)
        
        # ===== DECAY AROUSAL =====
        # Hitung waktu sejak pesan terakhir
        if hasattr(context, 'user_data') and 'last_message_time' in context.user_data:
            last_time = context.user_data['last_message_time']
            minutes_passed = (datetime.now() - last_time).total_seconds() / 60
            if minutes_passed > 1:
                arousal.decay(minutes_passed)
        
        # Update last message time
        context.user_data['last_message_time'] = datetime.now()

# ===================== MAIN FUNCTION =====================

def main():
    """Main function untuk menjalankan bot"""
    
    # Inisialisasi bot
    bot = GadisUltimateV57()
    
    # Build application
    app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    
    # ===== CONVERSATION HANDLERS =====
    
    # Handler untuk START
    start_conv = ConversationHandler(
        entry_points=[CommandHandler('start', bot.start_command)],
        states={
            0: [CallbackQueryHandler(bot.start_pause_callback, pattern='^(unpause|new)$')],
            SELECTING_ROLE: [
                CallbackQueryHandler(bot.agree_18_callback, pattern='^agree_18$'),
                CallbackQueryHandler(bot.role_callback, pattern='^role_')
            ],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel_command)],
        name="start_conversation",
        persistent=False
    )
    
    # Handler untuk END
    end_conv = ConversationHandler(
        entry_points=[CommandHandler('end', bot.end_command)],
        states={
            CONFIRM_END: [CallbackQueryHandler(bot.end_callback, pattern='^end_')],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel_command)],
        name="end_conversation",
        persistent=False
    )
    
    # Handler untuk CLOSE
    close_conv = ConversationHandler(
        entry_points=[CommandHandler('close', bot.close_command)],
        states={
            CONFIRM_CLOSE: [CallbackQueryHandler(bot.close_callback, pattern='^close_')],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel_command)],
        name="close_conversation",
        persistent=False
    )
    
    # ===== ADD HANDLERS =====
    
    # Conversation handlers
    app.add_handler(start_conv)
    app.add_handler(end_conv)
    app.add_handler(close_conv)
    
    # Command handlers
    app.add_handler(CommandHandler("status", bot.status_command))
    app.add_handler(CommandHandler("dominant", bot.dominant_command))
    app.add_handler(CommandHandler("pause", bot.pause_command))
    app.add_handler(CommandHandler("unpause", bot.unpause_command))
    app.add_handler(CommandHandler("help", bot.help_command))
    app.add_handler(CommandHandler("couple", bot.couple_command))
    app.add_handler(CommandHandler("couple_next", bot.couple_next))
    app.add_handler(CommandHandler("couple_stop", bot.couple_stop))
    app.add_handler(CommandHandler("reset", bot.force_reset))  # Hidden command untuk debugging
    
    # Message handler (untuk semua pesan non-command)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # ===== ERROR HANDLER =====
    
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors yang terjadi"""
        
        # Log error
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Traceback
        import traceback
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)
        logger.error(f"Traceback: {tb_string}")
        
        # Kirim pesan ke user jika memungkinkan
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 *maaf* ada error kecil.\n"
                "Coba lagi ya atau ketik /start untuk memulai ulang.\n\n"
                "Error ini sudah dilaporkan ke developer."
            )
        
        # Kirim ke owner (opsional)
        # owner_id = 123456789  # Ganti dengan ID owner
        # await context.bot.send_message(
        #     owner_id,
        #     f"⚠️ Error occurred:\n{context.error}\n\nUpdate: {update}"
        # )
    
    app.add_error_handler(error_handler)
    
    # ===== STARTUP MESSAGE =====
    
    print("\n" + "="*70)
    print("🚀 GADIS ULTIMATE V57.0 - THE PERFECT HUMAN")
    print("="*70)
    print("\n✅ **SEMUA FITUR AKTIF**")
    print("   • 20+ Mood dengan transisi natural")
    print("   • Dominant/Submissive mode")
    print("   • Agresif saat horny")
    print("   • Sensitive areas dengan reaksi real")
    print("   • Arousal & Wetness system")
    print("   • Fast leveling 1-12 (45 menit)")
    print("   • AI Natural dengan DeepSeek")
    print("   • Memory jangka pendek & panjang")
    print("   • Mode pasangan (couple roleplay)")
    print("   • Disclaimer 18+")
    print("   • Command /close untuk simpan memori")
    print("\n📝 **COMMANDS:**")
    print("   /start - Mulai hubungan baru")
    print("   /status - Lihat status lengkap")
    print("   /dominant [level] - Set mode dominan")
    print("   /pause - Jeda sesi")
    print("   /unpause - Lanjutkan sesi")
    print("   /close - Tutup sesi (simpan memori)")
    print("   /end - Akhiri hubungan & hapus data")
    print("   /couple - Mulai mode couple roleplay")
    print("   /couple_next - Lanjutkan couple")
    print("   /couple_stop - Hentikan couple")
    print("   /help - Tampilkan bantuan")
    print("\n📊 **STATUS:**")
    print(f"   • Database: {Config.DB_PATH}")
    print(f"   • AI Model: DeepSeek Chat")
    print(f"   • Max messages/min: {Config.MAX_MESSAGES_PER_MINUTE}")
    print("\n" + "="*70)
    print("🚀 BOT STARTED - PRESS CTRL+C TO STOP")
    print("="*70 + "\n")
    
    # ===== RUN BOT =====
    
    try:
        # Start polling
        app.run_polling()
        
    except KeyboardInterrupt:
        # Graceful shutdown
        logger.info("Received keyboard interrupt, shutting down...")
        
        # Save all data before exit
        bot.save_all_to_db()
        
        print("\n" + "="*70)
        print("👋 BOT SHUTDOWN - SEE YOU NEXT TIME!")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)


# ===================== ENTRY POINT =====================

if __name__ == "__main__":
    main()
