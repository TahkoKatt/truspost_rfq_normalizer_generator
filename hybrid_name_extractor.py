#!/usr/bin/env python3
"""
Hybrid Name Extractor: Regex + NER + LLM Validation
Three-stage approach for robust name extraction from business emails
"""

import re
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

@dataclass
class NameCandidate:
    """A potential name found by regex or NER"""
    text: str
    confidence: float
    method: str  # "zone_regex", "ner", "hybrid"
    zone_type: str  # "signature", "contact_instruction", "introduction", etc.
    context: str  # surrounding text for debugging

class HybridNameExtractor:
    """Three-stage name extraction: Zone Detection → NER → LLM Validation"""

    def __init__(self):
        """Initialize with spaCy NER and OpenAI client"""
        self.openai_client = self._init_openai()
        self.nlp = self._init_spacy()

    def _init_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            return OpenAI(api_key=api_key)
        return None

    def _init_spacy(self):
        """Initialize spaCy Spanish NER model"""
        try:
            import spacy
            return spacy.load("es_core_news_md")
        except Exception as e:
            print(f"Warning: Could not load spaCy Spanish model: {e}")
            try:
                import spacy
                return spacy.load("xx_ent_wiki_sm")  # fallback multilingual
            except:
                print("Warning: No spaCy model available, using regex only")
                return None

    def detect_name_zones(self, text: str) -> List[Dict[str, str]]:
        """
        Stage 1: Use regex/heuristics to detect candidate name zones
        Returns list of zones with their type and text content
        """
        zones = []
        text_lower = text.lower()

        # Define zone detection patterns with their types
        zone_patterns = [
            # Signature zones (high confidence)
            {
                'pattern': r'(saludos[^\n]*(?:\n[^\n]*){0,3})',
                'type': 'signature_saludos',
                'confidence': 0.9
            },
            {
                'pattern': r'(atentamente[^\n]*(?:\n[^\n]*){0,3})',
                'type': 'signature_atentamente',
                'confidence': 0.9
            },
            {
                'pattern': r'(gracias[^\n]*(?:\n[^\n]*){0,3})',
                'type': 'signature_gracias',
                'confidence': 0.8
            },
            {
                'pattern': r'(cordialmente[^\n]*(?:\n[^\n]*){0,3})',
                'type': 'signature_cordialmente',
                'confidence': 0.9
            },

            # Contact instruction zones (medium-high confidence)
            {
                'pattern': r'(contacto?[:\s]+[^\n.]{5,50})',
                'type': 'contact_instruction',
                'confidence': 0.8
            },
            {
                'pattern': r'(favor\s+de\s+contactar[^\n.]{5,50})',
                'type': 'contact_request',
                'confidence': 0.8
            },
            {
                'pattern': r'(comunicarse\s+con[^\n.]{5,50})',
                'type': 'contact_request',
                'confidence': 0.8
            },
            {
                'pattern': r'(llamar\s+a[^\n.]{5,50})',
                'type': 'contact_request',
                'confidence': 0.7
            },
            {
                'pattern': r'(dirigirse\s+a[^\n.]{5,50})',
                'type': 'contact_request',
                'confidence': 0.7
            },

            # Introduction zones (medium confidence)
            {
                'pattern': r'(soy\s+[^\n.]{3,30})',
                'type': 'self_introduction',
                'confidence': 0.7
            },
            {
                'pattern': r'(me\s+llamo\s+[^\n.]{3,30})',
                'type': 'self_introduction',
                'confidence': 0.8
            },
            {
                'pattern': r'(mi\s+nombre\s+es\s+[^\n.]{3,30})',
                'type': 'self_introduction',
                'confidence': 0.8
            },

            # Delegation zones (medium confidence)
            {
                'pattern': r'([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü\s]{5,40}\s+(?:se\s+encargará|manejará|atenderá))',
                'type': 'delegation',
                'confidence': 0.6
            },

            # Email signature blocks (catch-all, lower confidence)
            {
                'pattern': r'(\n[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü\s]{5,40}\n(?:[^\n]*(?:tel|email|whatsapp|phone)[^\n]*\n?){1,3})',
                'type': 'email_signature',
                'confidence': 0.6
            }
        ]

        # Extract zones
        for pattern_info in zone_patterns:
            matches = re.finditer(pattern_info['pattern'], text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                zone_text = match.group(1).strip()
                if zone_text and len(zone_text) > 3:
                    zones.append({
                        'text': zone_text,
                        'type': pattern_info['type'],
                        'confidence': pattern_info['confidence'],
                        'start': match.start(),
                        'end': match.end()
                    })

        # Sort by confidence and position (prefer end of email for signatures)
        zones.sort(key=lambda x: (x['confidence'], x['start']), reverse=True)

        return zones

    def extract_ner_candidates(self, zones: List[Dict]) -> List[NameCandidate]:
        """
        Stage 2: Apply NER to detected zones to find PERSON entities
        """
        candidates = []

        if not self.nlp:
            # Fallback to simple regex if no NER available
            return self.extract_regex_fallback_candidates(zones)

        for zone in zones:
            zone_text = zone['text']

            # Apply NER to the zone
            doc = self.nlp(zone_text)

            for ent in doc.ents:
                if ent.label_ == "PERSON" or ent.label_ == "PER":  # Person entities
                    name_text = ent.text.strip()

                    # Basic validation
                    if self._is_valid_name_candidate(name_text):
                        confidence = zone['confidence'] * 0.9  # NER found person in zone
                        candidates.append(NameCandidate(
                            text=name_text,
                            confidence=confidence,
                            method="ner",
                            zone_type=zone['type'],
                            context=zone_text
                        ))

        return candidates

    def extract_regex_fallback_candidates(self, zones: List[Dict]) -> List[NameCandidate]:
        """
        Fallback regex-based candidate extraction when NER is not available
        """
        candidates = []

        # Refined name patterns for Spanish business context
        name_patterns = [
            # After greetings (high confidence)
            (r'(?:saludos|atentamente|gracias|cordialmente)[,\s]*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})', 0.9),

            # Contact patterns (medium-high confidence)
            (r'contacto?[:\s]+([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})', 0.8),
            (r'favor\s+de\s+contactar\s+a?\s*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})', 0.8),
            (r'comunicarse\s+con\s+([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})', 0.8),

            # Introduction patterns (medium confidence)
            (r'(?:soy|me\s+llamo|mi\s+nombre\s+es)\s+([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})', 0.8),

            # Names before contact info (medium confidence)
            (r'([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3})(?=\s*(?:whatsapp|tel|email|phone|\+\d))', 0.7),

            # Generic Spanish name patterns (lower confidence)
            (r'\b([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+)\b', 0.5)
        ]

        for zone in zones:
            zone_text = zone['text']

            for pattern, pattern_confidence in name_patterns:
                matches = re.finditer(pattern, zone_text, re.IGNORECASE)
                for match in matches:
                    name_text = match.group(1).strip()

                    if self._is_valid_name_candidate(name_text):
                        # Combine zone confidence with pattern confidence
                        combined_confidence = zone['confidence'] * pattern_confidence

                        candidates.append(NameCandidate(
                            text=name_text,
                            confidence=combined_confidence,
                            method="zone_regex",
                            zone_type=zone['type'],
                            context=zone_text
                        ))

        return candidates

    def _is_valid_name_candidate(self, name: str) -> bool:
        """Validate if a candidate string could be a personal name"""
        if not name or len(name) < 3 or len(name) > 60:
            return False

        # Exclude common non-name words
        exclude_words = {
            'días', 'kg', 'euro', 'precio', 'toneladas', 'total', 'aproximadamente',
            'presupuesto', 'cotización', 'maquinas', 'envio', 'urgente', 'seguro',
            'fabrica', 'cliente', 'esperando', 'whatsapp', 'tel', 'email', 'company',
            'empresa', 'logistics', 'transporte', 'valencia', 'madrid', 'barcelona',
            'santos', 'brasil', 'spain', 'españa', 'mañana', 'hoy', 'ayer',
            'gracias', 'saludos', 'atentamente', 'contacto', 'favor', 'llamar',
            'phone', 'móvil', 'celular'
        }

        name_lower = name.lower()
        if any(word in name_lower for word in exclude_words):
            return False

        # Must have reasonable letter-to-number ratio
        letter_count = sum(c.isalpha() for c in name)
        if letter_count < len(name) * 0.8:  # At least 80% letters
            return False

        # Must start with capital letter
        if not name[0].isupper():
            return False

        # Check for valid Spanish name patterns
        words = name.split()
        if len(words) < 1 or len(words) > 4:
            return False

        # Each word should start with capital
        if not all(word[0].isupper() for word in words):
            return False

        return True

    def llm_validate_candidates(self, candidates: List[NameCandidate]) -> Optional[str]:
        """
        Stage 3: Use LLM to validate and select the best candidate
        """
        if not candidates:
            return None

        if not self.openai_client:
            # Fallback: return highest confidence candidate
            best_candidate = max(candidates, key=lambda x: x.confidence)
            return best_candidate.text

        # Prepare candidates for LLM validation
        candidate_list = []
        for i, candidate in enumerate(candidates[:5]):  # Limit to top 5
            candidate_list.append(f"{i+1}. {candidate.text} (found in {candidate.zone_type}, confidence: {candidate.confidence:.2f})")

        if not candidate_list:
            return None

        candidates_text = "\n".join(candidate_list)

        prompt = f"""You are an expert at identifying personal names in Spanish business emails.

From the following candidates extracted from an RFQ email, select the MOST LIKELY full human personal name.

CANDIDATES:
{candidates_text}

SELECTION CRITERIA:
- Must be a complete personal name (first + last name)
- Should be properly formatted (Title Case)
- Exclude company names, job titles, or technical terms
- Prefer names from signature sections or contact instructions
- Spanish names typically have 2-4 words (Nombre + Apellido(s))

Return ONLY the best personal name, or "NONE" if no valid personal name exists.

Examples of GOOD responses: "Juan Martinez", "María José García", "Carlos López Mendez"
Examples of BAD responses: "Logistics SL", "Contacto", "Valencia", "Manager"

Best personal name:"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.1
            )

            result = response.choices[0].message.content.strip()

            # Validate LLM response
            if result and result != "NONE" and self._is_valid_name_candidate(result):
                return result
            else:
                # LLM couldn't validate, fall back to highest confidence
                best_candidate = max(candidates, key=lambda x: x.confidence)
                return best_candidate.text if best_candidate.confidence > 0.5 else None

        except Exception as e:
            print(f"LLM validation failed: {e}")
            # Fallback to highest confidence candidate
            best_candidate = max(candidates, key=lambda x: x.confidence)
            return best_candidate.text if best_candidate.confidence > 0.5 else None

    def extract_name(self, text: str) -> Dict[str, any]:
        """
        Main extraction method: combines all three stages
        Returns dict with name, confidence, method, and debug info
        """
        # Stage 1: Detect name zones
        zones = self.detect_name_zones(text)

        if not zones:
            return {"name": "", "confidence": 0.0, "method": "no_zones", "debug": {"zones": []}}

        # Stage 2: Extract NER candidates from zones
        candidates = self.extract_ner_candidates(zones)

        if not candidates:
            return {"name": "", "confidence": 0.0, "method": "no_candidates", "debug": {"zones": zones}}

        # Stage 3: LLM validation and selection
        final_name = self.llm_validate_candidates(candidates)

        if final_name:
            # Calculate final confidence based on best candidate
            best_candidate = max(candidates, key=lambda x: x.confidence)
            confidence = min(best_candidate.confidence * 1.1, 1.0)  # Small boost for LLM validation
            method = f"hybrid_{best_candidate.method}"
        else:
            confidence = 0.0
            method = "validation_failed"

        return {
            "name": final_name or "",
            "confidence": confidence,
            "method": method,
            "debug": {
                "zones": len(zones),
                "candidates": [{"text": c.text, "confidence": c.confidence, "zone": c.zone_type} for c in candidates],
                "zones_detail": zones
            }
        }

# Test the hybrid extractor
if __name__ == "__main__":
    extractor = HybridNameExtractor()

    test_emails = [
        # Test case 1: Traditional signature
        """Necesitamos cotización urgente Valencia-Santos.

        Saludos
        Juan Martinez
        WhatsApp: +34 666 123 456""",

        # Test case 2: Contact instruction
        """Envío de maquinaria pesada.

        Favor de contactar a María García para más detalles.
        Tel: +34 91 123 4567""",

        # Test case 3: Self introduction
        """Hola, soy Carlos López de TransLogistics SL.

        Necesitamos presupuesto para envío a Brasil.""",

        # Test case 4: Complex real-world example
        """hola buenos dias!!

necesitamos cotizar un envio URGENTE de valencia españa al puerto de SANTOS brasil... son maquinarias pesadas de segunda mano aprox 2.5 toneladas + o -

tengo 3 maquinas:
- una cortadora que mide algo asi como 180x90x120 cm pesa 890kg mas o menos
- soldadora de 65kg (pequeña) 40x30x80
- compresor grande PESADO!!! 950kg aprox dimensiones 200x110x140 creo q son

TOTAL= mas o menos 1900kg pero pueden ser hasta 2200kg dependiendo de los accesorios

necesitamos que llegue antes del 15 de octubre por fabor es MUY urgente nuestro cliente ya esta esperando

pueden incluir SEGURO??? y el transporte hasta la fabrica en santos??

presupuesto???

saludos
juan martinez
WhatsApp: +34 666 123 456
Maquilogistics SL
valencia

PD: algunas maquinas tienen aceite residual pero ya las limpiamos"""
    ]

    for i, email in enumerate(test_emails, 1):
        print(f"\n🧪 TEST CASE {i}:")
        print("-" * 50)
        result = extractor.extract_name(email)
        print(f"✅ Extracted Name: '{result['name']}'")
        print(f"📊 Confidence: {result['confidence']:.1%}")
        print(f"🔧 Method: {result['method']}")
        print(f"🔍 Zones Found: {result['debug']['zones']}")
        print(f"🎯 Candidates: {len(result['debug']['candidates'])}")
        if result['debug']['candidates']:
            for c in result['debug']['candidates']:
                print(f"   - {c['text']} ({c['confidence']:.2f}, {c['zone']})")