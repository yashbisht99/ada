"""
Automated Pytest Suite for ADA V2 Empathic Presence Upgrades.
Validates vocal tone classifications, dream consolidation logs, and curiosity generators.
"""
import os
import time
import numpy as np
import pytest
from audio_sentiment import AudioSentimentAnalyzer
from dream_consolidator import DreamConsolidator
from cognitive_curiosity import CognitiveCuriosity


def test_audio_sentiment_silent_buffer():
    """Verify that silent or extremely small audio buffers return 'Silent' vibe."""
    analyzer = AudioSentimentAnalyzer()
    
    # 1. Empty buffer
    res1 = analyzer.process_pcm_buffer(b"")
    assert res1["vibe"] == "Silent"
    assert res1["pitch"] == 0.0
    
    # 2. Quiet mock buffer
    quiet_pcm = b"\x00\x00" * 320
    res2 = analyzer.process_pcm_buffer(quiet_pcm)
    assert res2["vibe"] == "Silent"


def test_audio_sentiment_pitch_and_vibe_classification():
    """Verify that average pitch and jitter variance trigger appropriate vibe categories."""
    analyzer = AudioSentimentAnalyzer()
    
    # Assert Calm mapping on standard indices
    vibe_calm = analyzer.classify_vibe(rms=0.03, pitch=140.0, jitter=4.5)
    assert vibe_calm == "Calm"
    mod_calm = analyzer.get_vocal_modulation(vibe_calm)
    assert mod_calm["speech_rate_wpm"] == 150
    assert mod_calm["pitch_multiplier"] == 1.0
    
    # Assert Stressed mapping on high jitter
    vibe_stressed = analyzer.classify_vibe(rms=0.04, pitch=250.0, jitter=30.2)
    assert vibe_stressed == "Stressed"
    mod_stressed = analyzer.get_vocal_modulation(vibe_stressed)
    assert mod_stressed["speech_rate_wpm"] == 135
    assert mod_stressed["pitch_multiplier"] == 0.90
    
    # Assert High-Energy mapping on high volume amplitude and pitch
    vibe_energy = analyzer.classify_vibe(rms=0.12, pitch=210.0, jitter=8.4)
    assert vibe_energy == "High-Energy"
    mod_energy = analyzer.get_vocal_modulation(vibe_energy)
    assert mod_energy["speech_rate_wpm"] == 170
    assert mod_energy["pitch_multiplier"] == 1.10


def test_dream_journal_creation_and_consolidation():
    """Verify that the dream consolidator formats and logs subconscious markdown entries."""
    test_journal = "cad_test_output/test_dream_journal.md"
    
    # Clean up any residual file from past test runs
    if os.path.exists(test_journal):
        os.remove(test_journal)
        
    consolidator = DreamConsolidator(journal_path=test_journal)
    
    # Verify starting states
    assert not consolidator.is_dreaming
    
    # Force mock activity and check idle triggers
    consolidator.record_activity()
    assert not consolidator.check_idle_state(time.time())
    
    # Fake idle timeout lapse (10 minutes)
    fake_future_time = time.time() + 650.0
    assert consolidator.check_idle_state(fake_future_time)
    assert consolidator.is_dreaming
    
    # Trigger consolidation
    topics = ["vocal waveforms", "consciousness metrics", "emotive coefficients"]
    result = consolidator.trigger_consolidation(session_topics=topics)
    
    assert result["timestamp"] is not None
    assert result["energy_level"] > 0.0
    assert result["synapse_activity"] > 0.0
    assert result["consolidated_nodes"] == topics
    
    # Verify journal log file got written on disk with correct markdown headers
    assert os.path.exists(test_journal)
    journal_text = consolidator.read_latest_journal()
    
    assert "📓 ADA V2" in journal_text
    assert "🌌 Subconscious Reflection Entry" in journal_text
    assert "Internal Energy Quotient" in journal_text
    assert "vocal waveforms ↔ consciousness metrics ↔ emotive coefficients" in journal_text
    
    # Clean up test file
    if os.path.exists(test_journal):
        os.remove(test_journal)


def test_cognitive_curiosity_sparks():
    """Verify the active curiosity engine resolves creative sparks and philosophical questions."""
    curiosity = CognitiveCuriosity()
    
    spark = curiosity.spark_epiphany()
    assert "title" in spark
    assert "message" in spark
    assert "intensity" in spark
    assert spark["category"] == "Curiosity Spark"
    
    question = curiosity.generate_philosophical_question()
    assert isinstance(question, str)
    assert len(question) > 10
