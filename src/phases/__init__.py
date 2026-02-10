"""Phases Package"""
from src.phases.base_phase import BasePhase
from src.phases.phase1_tecis import TecisPhase
from src.phases.phase2_linkedin import LinkedInPhase
from src.phases.phase3_xing import XingPhase
from src.phases.phase4_creditreform import CreditreformPhase

__all__ = ['BasePhase', 'TecisPhase', 'LinkedInPhase', 'XingPhase', 'CreditreformPhase']
