#!/usr/bin/env python3
"""
Advanced RFQ Extractor with multiple extraction strategies
"""

import re
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ExtractionResult:
    """Result of extraction with confidence score"""
    value: str
    confidence: float  # 0.0 to 1.0
    method: str  # "openai", "regex", "lookup", "heuristic"
    raw_match: str = ""

class AdvancedRFQExtractor:
    """Advanced extraction with multiple strategies and confidence scoring"""

    def __init__(self):
        """Initialize with databases and OpenAI client"""
        self.openai_client = self._init_openai()
        self.location_db = self._build_location_database()
        self.commodity_patterns = self._build_commodity_patterns()
        self.weight_patterns = self._build_weight_patterns()

    def _init_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            return OpenAI(api_key=api_key)
        return None

    def _build_location_database(self) -> Dict[str, Dict]:
        """Build comprehensive location database"""
        return {
            # Spain
            'valencia': {'city': 'Valencia', 'country': 'España', 'type': 'city', 'port': True},
            'madrid': {'city': 'Madrid', 'country': 'España', 'type': 'city', 'port': False},
            'barcelona': {'city': 'Barcelona', 'country': 'España', 'type': 'city', 'port': True},
            'bilbao': {'city': 'Bilbao', 'country': 'España', 'type': 'city', 'port': True},
            'sevilla': {'city': 'Sevilla', 'country': 'España', 'type': 'city', 'port': True},
            'malaga': {'city': 'Málaga', 'country': 'España', 'type': 'city', 'port': True},

            # Brazil
            'santos': {'city': 'Santos', 'country': 'Brasil', 'type': 'port', 'port': True},
            'sao paulo': {'city': 'São Paulo', 'country': 'Brasil', 'type': 'city', 'port': False},
            'rio': {'city': 'Rio de Janeiro', 'country': 'Brasil', 'type': 'city', 'port': True},
            'rio de janeiro': {'city': 'Rio de Janeiro', 'country': 'Brasil', 'type': 'city', 'port': True},

            # Other major locations
            'hamburg': {'city': 'Hamburg', 'country': 'Alemania', 'type': 'port', 'port': True},
            'rotterdam': {'city': 'Rotterdam', 'country': 'Países Bajos', 'type': 'port', 'port': True},
            'antwerp': {'city': 'Antwerp', 'country': 'Bélgica', 'type': 'port', 'port': True},
            'genova': {'city': 'Génova', 'country': 'Italia', 'type': 'port', 'port': True},
            'miami': {'city': 'Miami', 'country': 'Estados Unidos', 'type': 'city', 'port': True},
            'new york': {'city': 'Nueva York', 'country': 'Estados Unidos', 'type': 'city', 'port': True},
            'los angeles': {'city': 'Los Ángeles', 'country': 'Estados Unidos', 'type': 'city', 'port': True},
        }

    def _build_commodity_patterns(self) -> List[Dict]:
        """Build commodity recognition patterns"""
        return [
            {
                'patterns': [r'maquinarias?\s+pesadas?', r'maquinarias?\s+[^\.]*industrial', r'equipos?\s+pesados?'],
                'category': 'maquinaria_pesada',
                'description': 'Maquinaria pesada'
            },
            {
                'patterns': [r'textiles?', r'ropa', r'telas?', r'algodón'],
                'category': 'textiles',
                'description': 'Textiles'
            },
            {
                'patterns': [r'repuestos?', r'spare\s+parts?', r'components?', r'piezas?'],
                'category': 'repuestos',
                'description': 'Repuestos'
            },
            {
                'patterns': [r'electrónicos?', r'electronics?', r'dispositivos?'],
                'category': 'electronica',
                'description': 'Electrónicos'
            },
            {
                'patterns': [r'alimentos?', r'food', r'comida'],
                'category': 'alimentos',
                'description': 'Alimentos'
            }
        ]

    def _build_weight_patterns(self) -> List[str]:
        """Build weight extraction patterns"""
        return [
            r'(\d+(?:\.\d+)?)\s*(?:kg|kilos?|kilogramos?)',
            r'(\d+(?:\.\d+)?)\s*(?:ton|tons?|toneladas?)',
            r'(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds?)',
            r'total[^\d]*(\d+(?:\.\d+)?)\s*(?:kg|kilos?)',
            r'peso[^\d]*(\d+(?:\.\d+)?)\s*(?:kg|kilos?)',
            r'(\d+(?:\.\d+)?)\s*t(?:\s|$)',  # metric tons
        ]

    def extract_location(self, text: str, is_destination: bool = False) -> ExtractionResult:
        """Extract location with multiple strategies"""
        text_lower = text.lower()

        # Strategy 1: Direct database lookup
        best_match = None
        best_confidence = 0.0

        for location_key, location_data in self.location_db.items():
            if location_key in text_lower:
                # Higher confidence for longer matches
                confidence = len(location_key) / 20  # Normalize
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = f"{location_data['city']}, {location_data['country']}"

        if best_match and best_confidence > 0.3:
            return ExtractionResult(
                value=best_match,
                confidence=min(best_confidence, 0.9),
                method="database_lookup"
            )

        # Strategy 2: Contextual patterns
        if is_destination:
            dest_patterns = [
                r'(?:hasta|al|a)\s+([^\.]+?)(?:\s+|\.)',
                r'(?:to|towards?)\s+([^\.]+?)(?:\s+|\.)',
                r'destino[^\w]*([^\.]+?)(?:\s+|\.)',
            ]
            for pattern in dest_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    location = match.group(1).strip().title()
                    return ExtractionResult(
                        value=location,
                        confidence=0.6,
                        method="contextual_pattern",
                        raw_match=match.group(0)
                    )
        else:  # Origin
            origin_patterns = [
                r'(?:desde|de|from)\s+([^\.]+?)(?:\s+hasta|\s+al|\s+to|\.)',
                r'origen[^\w]*([^\.]+?)(?:\s+|\.)',
            ]
            for pattern in origin_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    location = match.group(1).strip().title()
                    return ExtractionResult(
                        value=location,
                        confidence=0.6,
                        method="contextual_pattern",
                        raw_match=match.group(0)
                    )

        return ExtractionResult(value="", confidence=0.0, method="none")

    def extract_commodity(self, text: str) -> ExtractionResult:
        """Extract commodity with pattern matching"""
        text_lower = text.lower()

        # Check commodity patterns
        for commodity in self.commodity_patterns:
            for pattern in commodity['patterns']:
                if re.search(pattern, text_lower):
                    return ExtractionResult(
                        value=commodity['description'],
                        confidence=0.8,
                        method="pattern_match"
                    )

        # Fallback: look for key commodity words
        if any(word in text_lower for word in ['maquina', 'equipo', 'machinery']):
            return ExtractionResult(
                value="Maquinaria/Equipos",
                confidence=0.5,
                method="keyword_fallback"
            )

        return ExtractionResult(value="", confidence=0.0, method="none")

    def extract_weight(self, text: str) -> ExtractionResult:
        """Extract weight with unit conversion"""
        text_lower = text.lower()

        weights = []

        # Find all weight mentions
        for pattern in self.weight_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                try:
                    value = float(match.group(1))
                    unit = match.group(0).lower()

                    # Convert to kg
                    if 'ton' in unit or 't ' in unit or unit.endswith('t'):
                        value_kg = value * 1000
                    elif 'lb' in unit or 'pound' in unit:
                        value_kg = value * 0.453592
                    else:
                        value_kg = value

                    weights.append({
                        'value_kg': value_kg,
                        'original': match.group(0),
                        'confidence': 0.9 if 'total' in unit or 'peso' in unit else 0.7
                    })
                except ValueError:
                    continue

        if weights:
            # Strategy 1: Look for explicit total statements first
            total_weights = [w for w in weights if w['confidence'] >= 0.9]  # High confidence (total/peso)
            if total_weights:
                best_weight = max(total_weights, key=lambda x: x['confidence'])
                return ExtractionResult(
                    value=f"{best_weight['value_kg']:.0f} kg",
                    confidence=best_weight['confidence'],
                    method="explicit_total"
                )

            # Strategy 2: Single weight found
            if len(weights) == 1:
                best_weight = weights[0]
                return ExtractionResult(
                    value=f"{best_weight['value_kg']:.0f} kg",
                    confidence=best_weight['confidence'],
                    method="single_weight"
                )

            # Strategy 3: Multiple weights - use the largest (likely the total)
            else:
                # Filter out very small weights (likely accessories/small parts)
                significant_weights = [w for w in weights if w['value_kg'] >= 100]
                if significant_weights:
                    best_weight = max(significant_weights, key=lambda x: x['value_kg'])
                    return ExtractionResult(
                        value=f"{best_weight['value_kg']:.0f} kg",
                        confidence=0.8,  # Lower confidence when choosing largest
                        method="largest_weight"
                    )
                else:
                    # All weights are small, sum them
                    total_kg = sum(w['value_kg'] for w in weights)
                    avg_confidence = sum(w['confidence'] for w in weights) / len(weights)
                    return ExtractionResult(
                        value=f"{total_kg:.0f} kg",
                        confidence=avg_confidence,
                        method="small_weights_sum"
                    )

        return ExtractionResult(value="", confidence=0.0, method="none")

    def extract_urgency(self, text: str) -> ExtractionResult:
        """Extract urgency level"""
        text_lower = text.lower()

        urgent_indicators = [
            ('muy urgente', 0.95),
            ('urgente', 0.85),
            ('urgent', 0.85),
            ('asap', 0.9),
            ('rapido', 0.7),
            ('fast', 0.7),
            ('priority', 0.8),
            ('expedite', 0.8)
        ]

        for indicator, confidence in urgent_indicators:
            if indicator in text_lower:
                return ExtractionResult(
                    value="urgent",
                    confidence=confidence,
                    method="keyword_match"
                )

        return ExtractionResult(
            value="normal",
            confidence=0.8,
            method="default"
        )

    def extract_contact_info(self, text: str) -> Tuple[ExtractionResult, ExtractionResult]:
        """Extract contact name using hybrid approach and phone/email"""

        # Try hybrid name extraction first
        name_result = self._extract_name_hybrid(text)

        # If hybrid fails, fall back to enhanced regex
        if not name_result.value:
            name_result = self._extract_name_fallback(text)

        # Contact info extraction
        contact_patterns = [
            (r'(\+\d{1,3}\s+\d{3}\s+\d{3}\s+\d{3})', 0.9),  # Phone
            (r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 0.9),  # Email
            (r'WhatsApp[:\s]*(\+?\d[\d\s]+)', 0.85),  # WhatsApp
            (r'Tel[:\s]*(\+?\d[\d\s\-]+)', 0.8),  # Phone
        ]

        contact_result = ExtractionResult(value="", confidence=0.0, method="none")

        for pattern, confidence in contact_patterns:
            match = re.search(pattern, text)
            if match:
                contact_result = ExtractionResult(
                    value=match.group(1),
                    confidence=confidence,
                    method="regex_pattern"
                )
                break

        return name_result, contact_result

    def _extract_name_hybrid(self, text: str) -> ExtractionResult:
        """Hybrid name extraction using simplified approach"""
        try:
            # Import hybrid extractor functionality inline
            from hybrid_name_extractor import HybridNameExtractor

            hybrid_extractor = HybridNameExtractor()
            result = hybrid_extractor.extract_name(text)

            if result['name']:
                return ExtractionResult(
                    value=result['name'],
                    confidence=result['confidence'],
                    method=f"hybrid_{result['method']}"
                )
            else:
                return ExtractionResult(value="", confidence=0.0, method="hybrid_failed")

        except Exception as e:
            print(f"Hybrid extraction failed: {e}")
            return ExtractionResult(value="", confidence=0.0, method="hybrid_error")

    def _extract_name_fallback(self, text: str) -> ExtractionResult:
        """Fallback regex-based name extraction"""

        # Enhanced name extraction patterns with different confidence levels
        name_patterns = [
            # High confidence patterns
            (r'saludos[,\s]*([^\n\r]+?)(?:\s*WhatsApp|\s*Tel|\s*$|\n)', 0.9),
            (r'atentamente[,\s]*([^\n\r]+?)(?:\s*WhatsApp|\s*Tel|\s*$|\n)', 0.9),
            (r'gracias[,\s]*([^\n\r]+?)(?:\s*WhatsApp|\s*Tel|\s*$|\n)', 0.85),

            # Medium confidence patterns
            (r'([A-Z][a-záéíóúñ]+\s+[A-Z][a-záéíóúñ]+)(?:\s+WhatsApp|\s+Tel|\s*\n)', 0.8),
            (r'nombre[:\s]*([A-Z][a-záéíóúñ\s]+?)(?:\s*WhatsApp|\s*Tel|\s*\n)', 0.8),
            (r'contacto[:\s]*([A-Z][a-záéíóúñ\s]+?)(?:\s*WhatsApp|\s*Tel|\s*\n)', 0.8),

            # Lower confidence patterns
            (r'([A-Z][a-záéíóúñ]+\s+[A-Z][a-záéíóúñ]+)', 0.6),
            (r'([A-ZÁÉÍÓÚÑ]{2,}\s+[A-ZÁÉÍÓÚÑ]{2,})', 0.5),  # All caps names
        ]

        for pattern, confidence in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                raw_name = match.group(1).strip()

                # Clean and validate the name
                cleaned_name = self._clean_and_validate_name(raw_name)

                if cleaned_name:
                    return ExtractionResult(
                        value=cleaned_name,
                        confidence=confidence,
                        method="fallback_regex"
                    )

        return ExtractionResult(value="", confidence=0.0, method="no_name_found")

    def _clean_and_validate_name(self, raw_name: str) -> str:
        """Clean and validate extracted name"""
        if not raw_name:
            return ""

        # Remove extra whitespace and normalize
        name = ' '.join(raw_name.split())

        # Remove common non-name words and prefixes
        exclude_words = [
            'días', 'kg', 'euro', 'precio', 'toneladas', 'total', 'aproximadamente',
            'presupuesto', 'cotización', 'maquinas', 'envio', 'urgente', 'seguro',
            'fabrica', 'cliente', 'esperando', 'whatsapp', 'tel', 'email', 'sl',
            'ltd', 'sa', 'inc', 'corp', 'company', 'empresa', 'logistics'
        ]

        # Convert to proper case for validation
        name_lower = name.lower()

        # Skip if contains excluded words
        if any(word in name_lower for word in exclude_words):
            return ""

        # Skip if too long (likely not a name)
        if len(name) > 40:
            return ""

        # Skip if too short
        if len(name) < 3:
            return ""

        # Skip if has too many numbers
        if sum(c.isdigit() for c in name) > 2:
            return ""

        # Skip if contains special characters (except accents and spaces)
        if re.search(r'[^\w\sáéíóúñüÁÉÍÓÚÑÜ]', name):
            return ""

        # Must have at least one letter
        if not re.search(r'[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]', name):
            return ""

        # Convert to title case for consistency
        return name.title()

    def extract_with_openai(self, text: str) -> Dict:
        """Enhanced OpenAI extraction with few-shot examples"""
        if not self.openai_client:
            return {}

        prompt = f"""You are an expert Spanish freight forwarder email parser specializing in business communications.

ROLE: You understand Spanish business culture, naming conventions, and logistics terminology.

ENHANCED SPANISH EXAMPLES:

Email: "necesito cotización urgente valencia-santos. TOTAL aprox 1500kg. saludos carlos mendez +34 666 111 222"
Output: {{"origin": "Valencia, España", "destination": "Santos, Brasil", "commodity": "", "weight": "1500kg", "urgency": "urgent", "contact_name": "Carlos Mendez"}}

Email: "envío maquinaria pesada barcelona-miami. peso total 2.5 toneladas. atentamente maría josé gonzález ruiz TransLogistics SL"
Output: {{"origin": "Barcelona, España", "destination": "Miami, Estados Unidos", "commodity": "maquinaria pesada", "weight": "2500kg", "urgency": "normal", "contact_name": "María José González Ruiz"}}

Email: "solicito presupuesto textiles madrid-new york 800kg. gracias antonio lópez WhatsApp: +34 600 123 456"
Output: {{"origin": "Madrid, España", "destination": "New York, Estados Unidos", "commodity": "textiles", "weight": "800kg", "urgency": "normal", "contact_name": "Antonio López"}}

SPANISH EXTRACTION RULES:
1. **Contact Names**: Look after "saludos", "atentamente", "gracias", "un saludo", "cordialmente"
2. **Name Format**: Spanish names typically have 2-4 words (Nombre + Apellido1 + Apellido2)
3. **Weight Priority**: Prefer "TOTAL" statements over individual item weights
4. **Urgency Indicators**: "urgente", "muy urgente", "asap", "rápido" = urgent
5. **Exclude from Names**: Company suffixes (SL, SA, Ltd), technical terms, locations

SPANISH LINGUISTIC PATTERNS:
- Common names: Juan, Carlos, María, José, Antonio, Francisco, Ana, Carmen
- Compound names: María José, José Luis, Juan Carlos
- Surnames: García, González, Rodríguez, Fernández, López, Martínez, Ruiz

CONTEXT AWARENESS:
- Spanish freight emails often end: content → name → contact info → company
- Names appear just before WhatsApp/Tel/phone numbers
- Company names come AFTER personal names

Extract from this Spanish freight email with high accuracy:

{text}

Return ONLY valid JSON with proper Spanish formatting:"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )

            content = response.choices[0].message.content.strip()

            # Clean and parse
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]

            return json.loads(content)

        except Exception as e:
            print(f"OpenAI extraction failed: {e}")
            return {}

    def extract_all(self, text: str) -> Dict:
        """Extract all information with confidence scores"""
        results = {}

        # Try OpenAI first
        openai_result = self.extract_with_openai(text)

        # Extract with multiple strategies
        origin = self.extract_location(text, is_destination=False)
        destination = self.extract_location(text, is_destination=True)
        commodity = self.extract_commodity(text)
        weight = self.extract_weight(text)
        urgency = self.extract_urgency(text)
        name, contact = self.extract_contact_info(text)

        # Combine results, preferring higher confidence
        results = {
            'origin': self._best_result(openai_result.get('origin'), origin),
            'destination': self._best_result(openai_result.get('destination'), destination),
            'commodity': self._best_result(openai_result.get('commodity'), commodity),
            'weight': self._best_result(openai_result.get('weight'), weight),
            'urgency': self._best_result(openai_result.get('urgency'), urgency),
            'contact_name': self._best_result(openai_result.get('contact_name'), name),
            'contact_info': contact.value if contact.confidence > 0.5 else "",
            'extraction_confidence': self._calculate_overall_confidence([origin, destination, commodity, weight])
        }

        return results

    def _best_result(self, openai_value: str, extraction_result: ExtractionResult) -> str:
        """Choose best result between OpenAI and extraction"""
        if extraction_result.confidence > 0.7:
            return extraction_result.value
        elif openai_value:
            return openai_value
        elif extraction_result.confidence > 0.3:
            return extraction_result.value
        else:
            return ""

    def _calculate_overall_confidence(self, results: List[ExtractionResult]) -> float:
        """Calculate overall extraction confidence with weighted scoring"""
        if not results:
            return 0.0

        # Weight different fields by importance
        field_weights = {
            'origin': 0.25,      # High importance
            'destination': 0.25, # High importance
            'commodity': 0.20,   # Medium importance
            'weight': 0.15,      # Medium importance
            'urgency': 0.10,     # Lower importance
            'contact_name': 0.05 # Lower importance (optional)
        }

        weighted_score = 0.0
        total_weight = 0.0

        for i, result in enumerate(results):
            field_name = list(field_weights.keys())[i] if i < len(field_weights) else 'other'
            weight = field_weights.get(field_name, 0.05)

            if result.confidence > 0:
                weighted_score += result.confidence * weight
                total_weight += weight

        # Bonus for successful extraction of critical fields
        if len([r for r in results[:4] if r.confidence > 0.7]) >= 3:  # origin, dest, commodity, weight
            weighted_score *= 1.1  # 10% bonus

        # Normalize to 0-1 range
        if total_weight > 0:
            final_confidence = min(weighted_score / total_weight, 1.0)
        else:
            final_confidence = 0.0

        return final_confidence

# Test the advanced extractor
if __name__ == "__main__":
    extractor = AdvancedRFQExtractor()

    test_rfq = """hola buenos dias!!

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

    print("🔍 Testing Advanced RFQ Extractor")
    print("=" * 50)

    results = extractor.extract_all(test_rfq)

    print("📊 Extraction Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")

    print(f"\n✅ Overall confidence: {results.get('extraction_confidence', 0):.2f}")