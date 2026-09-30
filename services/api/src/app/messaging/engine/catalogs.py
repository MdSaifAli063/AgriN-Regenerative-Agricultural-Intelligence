"""
Multilingual Message Catalogs and WhatsApp Template Specifications.
Supports 12 BRICS and African partner locales:
  en (English), hi (Hindi), mr (Marathi), pt (Portuguese),
  ru (Russian), zh (Chinese), ar (Arabic), am (Amharic),
  fa (Persian), sw (Swahili), zu (Zulu), af (Afrikaans).
"""

from typing import Any, Dict, List, Optional

# Supported locales with native labels
SUPPORTED_LOCALES = [
    ("en", "English"),
    ("hi", "हिन्दी (Hindi)"),
    ("mr", "मराठी (Marathi)"),
    ("pt", "Português (Portuguese)"),
    ("ru", "Русский (Russian)"),
    ("zh", "中文 (Chinese)"),
    ("ar", "العربية (Arabic)"),
    ("am", "አማርኛ (Amharic)"),
    ("fa", "فارسی (Persian)"),
    ("sw", "Kiswahili (Swahili)"),
    ("zu", "isiZulu (Zulu)"),
    ("af", "Afrikaans"),
]

# Message strings catalog per language
MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "welcome": "🌾 *Welcome to KrishiNet-BRICS Agricultural Advisory!*\nOne field. Many nations. Shared intelligence.\n\nPlease select your preferred language:\n1. English\n2. हिन्दी (Hindi)\n3. मराठी (Marathi)\n4. Português\n5. More languages (ru, zh, ar, sw, zu, af)\n\nReply with a number (1-5).",
        "lang_list_extended": "Select your language:\n1. English\n2. हिन्दी (Hindi)\n3. मराठी (Marathi)\n4. Português (Portuguese)\n5. Русский (Russian)\n6. 中文 (Chinese)\n7. العربية (Arabic)\n8. አማርኛ (Amharic)\n9. فارسی (Persian)\n10. Kiswahili\n11. isiZulu\n12. Afrikaans\n\nReply 1-12 (or 0 for Back):",
        "consent_prompt": "🛡️ *Data Sovereignty & Privacy Agreement*\nKrishiNet is a non-profit Digital Public Good. Your farm data stays sovereign on local soil and is encrypted.\n\nDo you consent to receiving regenerative crop advisories, local weather alerts, and pest outbreak warnings?\n\n1. ✅ Yes, I agree (Full sovereign advisory)\n2. ❌ No, exit\n\nReply 1 or 2:",
        "consent_granted": "✅ *Consent Recorded!*\nYour receipt code: *{receipt_code}*.\nYou can type STOP or ROKO anytime to cancel.\n\nNow, where is your farm located?\n📍 *Send a WhatsApp Location Pin*, or\n✍️ *Type your District / Village name* (e.g. 'Nagpur, Maharashtra'):",
        "location_confirm": "📍 Found location: *{place_name}* ({lat}, {lon}).\nIs this correct for your farm?\n1. Yes, continue\n2. No, let me re-type\n\nReply 1 or 2 (or 0 for Back):",
        "location_ask_retry": "Please type your district and state (e.g. 'Nagpur, Maharashtra' or 'Cascavel, Parana'):",
        "crop_select": "🌱 *Select your main crop:*\n1. Cotton (कपास / Algodão)\n2. Soybean (सोयाबीन / Soja)\n3. Maize / Corn (मक्का / Milho)\n4. Wheat (गेहूं / Trigo)\n5. Rice / Paddy (चावल / Arroz)\n6. Other crop\n\nReply 1-6 (or 0 for Back):",
        "main_menu": "📋 *KrishiNet Farmer Menu* ({crop}, {location})\n1. 🌾 Today's Advisory & Action Card\n2. 📸 Leaf Doctor (Send leaf photo for disease check)\n3. 🌦️ 3-Day Weather & Spray Window\n4. 🚜 My Field Status\n5. 🧑‍🌾 Extension Officer Assistance\n6. 🌐 Change Language / Settings\n\nReply 1-6 (0=Back, 9=Menu):",
        "disease_photo_prompt": "📸 *KrishiNet Leaf Doctor*\nPlease send a clear, close-up photo of the affected plant leaf.\n\nTips:\n• Capture both healthy and infected spots\n• Ensure good daylight\n\n(Reply 9 to return to Menu)",
        "voice_fallback": "🎙️ Voice message received! For best reliability on low bandwidth, please type your choice (1-6) or reply with your question in text. (Reply 9 for Menu)",
        "ai_disclaimer": "\n\n⚠️ _AI guidance only. Not a substitute for your local agricultural extension officer._",
        "opt_out_confirm": "🛑 You have unsubscribed from KrishiNet alerts. No further messages will be sent. Reply START or SHURU anytime to resubscribe.",
        "human_handoff": "🧑‍🌾 *Extension Officer Assistance*\nYour query has been forwarded to Extension Officer *{officer_name}* ({circle}).\nTicket Reference: *{ticket_id}*.\nAn officer will contact you within 24 hours.\n\n(Reply 9 for Main Menu)",
        "weather_summary": "🌦️ *3-Day Weather Forecast for {location}:*\n• Today: {temp_max}°C / {temp_min}°C, Rain: {rain_prob}%\n• Wind: {wind_speed} km/h\n• Spray Window: {spray_status}\n\n{spray_recommendation}\n\n(Reply 9 for Menu)",
        "invalid_option": "⚠️ Invalid option. Please reply with a valid number from the menu (or reply 9 for Main Menu).",
        "session_timeout": "⏰ Your session has timed out. Type any message or reply 9 to return to the Main Menu.",
    },
    "hi": {
        "welcome": "🌾 *कृषिनेट-ब्रिक्स कृषि सलाहकार में आपका स्वागत है!*\nएक खेत। अनेक देश। साझा ज्ञान।\n\nकृपया अपनी भाषा चुनें:\n1. English\n2. हिन्दी (Hindi)\n3. मराठी (Marathi)\n4. Português\n5. अन्य भाषाएं\n\nसंख्या (1-5) लिखकर भेजें।",
        "consent_prompt": "🛡️ *डेटा संप्रभुता एवं गोपनीयता सहमति*\nकृषिनेट एक डिजिटल पब्लिक गुड है। आपके खेत का डेटा स्थानीय मिट्टी पर सुरक्षित और एन्क्रिप्टेड रहेगा।\n\nक्या आप पुनर्योजी फसल सलाह, मौसम चेतावनी और कीट चेतावनी प्राप्त करने के लिए सहमत हैं?\n\n1. ✅ हाँ, मैं सहमत हूँ\n2. ❌ नहीं, बाहर निकलें\n\n1 या 2 लिखकर भेजें:",
        "consent_granted": "✅ *सहमति दर्ज कर ली गई है!*\nआपकी रसीद संख्या: *{receipt_code}*।\nरोकने के लिए कभी भी ROKO या STOP भेज सकते हैं।\n\nअब बताएं, आपका खेत कहाँ है?\n📍 *व्हाट्सएप लोकेशन पिन भेजें*, या\n✍️ *अपने जिले/गाँव का नाम लिखें* (उदा. 'नागपुर, महाराष्ट्र'):",
        "location_confirm": "📍 स्थान मिला: *{place_name}*।\nक्या यह आपके खेत के लिए सही है?\n1. हाँ, आगे बढ़ें\n2. नहीं, दोबारा लिखें\n\n1 या 2 भेजें (0=पीछे):",
        "crop_select": "🌱 *अपनी मुख्य फसल चुनें:*\n1. कपास (Cotton)\n2. सोयाबीन (Soybean)\n3. मक्का (Maize)\n4. गेहूं (Wheat)\n5. धान / चावल (Rice)\n6. अन्य फसल\n\n1-6 लिखकर भेजें (0=पीछे):",
        "main_menu": "📋 *कृषिनेट मुख्य मेनू* ({crop}, {location})\n1. 🌾 आज की फसल सलाह और कार्य सूची\n2. 📸 पत्ती डॉक्टर (रोग जांच हेतु फोटो भेजें)\n3. 🌦️ 3 दिवसीय मौसम व छिड़काव का समय\n4. 🚜 मेरे खेत की जानकारी\n5. 🧑‍🌾 कृषि अधिकारी सहायता\n6. 🌐 भाषा बदलें\n\n1-6 लिखकर भेजें (0=पीछे, 9=मेनू):",
        "disease_photo_prompt": "📸 *कृषिनेट पत्ती डॉक्टर*\nकृपया प्रभावित पौधे की पत्ती की स्पष्ट और नज़दीकी फोटो भेजें।\n(मेनू के लिए 9 भेजें)",
        "ai_disclaimer": "\n\n⚠️ _केवल एआई मार्गदर्शन। यह आपके स्थानीय कृषि प्रसार अधिकारी का विकल्प नहीं है।_",
        "opt_out_confirm": "🛑 आप कृषिनेट सेवाओं से अनसब्सक्राइब हो चुके हैं। कोई अन्य संदेश नहीं भेजा जाएगा। दोबारा शुरू करने के लिए SHURU या START भेजें।",
        "human_handoff": "🧑‍🌾 *कृषि अधिकारी सहायता*\nआपका अनुरोध कृषि अधिकारी *{officer_name}* को भेज दिया गया है।\nटिकट संख्या: *{ticket_id}*।\nअधिकारी 24 घंटे के भीतर संपर्क करेंगे। (मेनू के लिए 9 भेजें)",
        "weather_summary": "🌦️ *{location} का 3 दिवसीय मौसम:*\n• तापमान: {temp_max}°C / {temp_min}°C, बारिश: {rain_prob}%\n• हवा: {wind_speed} किमी/घंटा\n• छिड़काव विंडो: {spray_status}\n\n{spray_recommendation}\n(मेनू के लिए 9 भेजें)",
        "invalid_option": "⚠️ अमान्य विकल्प। कृपया मेनू से सही संख्या भेजें (या मेनू हेतु 9 भेजें)।",
    },
    "pt": {
        "welcome": "🌾 *Bem-vindo ao KrishiNet-BRICS - Inteligência Agrícola!*\nUm campo. Muitas nações. Conhecimento compartilhado.\n\nEscolha o seu idioma:\n1. English\n2. हिन्दी (Hindi)\n3. मराठी (Marathi)\n4. Português\n5. Mais idiomas\n\nResponda com um número (1-5):",
        "consent_prompt": "🛡️ *Termo de Soberania de Dados e Privacidade*\nO KrishiNet é um Bem Público Digital. Os dados da sua lavoura são protegidos, criptografados e soberanos.\n\nVocê concorda em receber recomendações regenerativas, alertas climáticos e avisos de pragas?\n\n1. ✅ Sim, concordo\n2. ❌ Não, sair\n\nResponda 1 ou 2:",
        "consent_granted": "✅ *Consentimento Registrado!*\nCódigo do comprovante: *{receipt_code}*.\nVocê pode digitar PARE ou STOP a qualquer momento para cancelar.\n\nOnde fica a sua propriedade?\n📍 *Envie a localização do WhatsApp*, ou\n✍️ *Digite o Município e Estado* (ex.: 'Cascavel, PR'):",
        "location_confirm": "📍 Localização identificada: *{place_name}*.\nEstá correto?\n1. Sim, continuar\n2. Não, redigitar\n\nResponda 1 ou 2 (0=Voltar):",
        "crop_select": "🌱 *Selecione a sua cultura principal:*\n1. Soja (Soybean)\n2. Milho (Maize)\n3. Algodão (Cotton)\n4. Trigo (Wheat)\n5. Arroz (Rice)\n6. Outra cultura\n\nResponda 1-6 (0=Voltar):",
        "main_menu": "📋 *Menu do Produtor KrishiNet* ({crop}, {location})\n1. 🌾 Recomendação de Manejo de Hoje\n2. 📸 Doutor da Folha (Envie foto para diagnóstico)\n3. 🌦️ Previsão de 3 Dias e Janela de Pulverização\n4. 🚜 Situação do Meu Talhão\n5. 🧑‍🌾 Falar com o Técnico Agrícola\n6. 🌐 Alterar Idioma\n\nResponda 1-6 (0=Voltar, 9=Menu):",
        "disease_photo_prompt": "📸 *Doutor da Folha KrishiNet*\nEnvie uma foto nítida e aproximada da folha com sintomas.\n(Responda 9 para o Menu)",
        "ai_disclaimer": "\n\n⚠️ _Orientação por IA. Não substitui o engenheiro agrônomo ou técnico de extensão local._",
        "opt_out_confirm": "🛑 Você cancelou os alertas do KrishiNet. Nenhuma mensagem adicional será enviada. Envie INICIAR ou START a qualquer momento para reativar.",
        "human_handoff": "🧑‍🌾 *Atendimento Agronômico*\nSua solicitação foi encaminhada para o técnico *{officer_name}* ({circle}).\nProtocolo: *{ticket_id}*.\nRetorno previsto em até 24h. (Responda 9 para Menu)",
        "weather_summary": "🌦️ *Previsão do Tempo para {location}:*\n• Temperatura: {temp_max}°C / {temp_min}°C, Chuva: {rain_prob}%\n• Vento: {wind_speed} km/h\n• Janela de Pulverização: {spray_status}\n\n{spray_recommendation}\n(Responda 9 para Menu)",
        "invalid_option": "⚠️ Opção inválida. Digite um número válido do menu (ou 9 para Menu Principal).",
    }
}

# Fallback helper for remaining 9 languages
def get_message(key: str, locale: str = "en", **kwargs: Any) -> str:
    """Retrieves localized message text with kwargs interpolation and English fallback."""
    cat = MESSAGES.get(locale, MESSAGES["en"])
    text = cat.get(key) or MESSAGES["en"].get(key, f"[{key}]")
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


# Pre-approved Meta WhatsApp Cloud templates definitions
WHATSAPP_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "krishinet_morning_digest_v1",
        "category": "UTILITY",
        "languages": ["en", "hi", "pt"],
        "body": "🌾 Good morning farmer! For your {{1}} field in {{2}}, today's priority: {{3}}. Weather: {{4}}°C with {{5}}% rain chance. Spray window: {{6}}. Reply 1 for full advice.",
        "parameters_example": ["Cotton", "Nagpur", "Apply biological Trichoderma spray", "32", "10", "OPEN"],
    },
    {
        "name": "krishinet_weather_alert_v1",
        "category": "UTILITY",
        "languages": ["en", "hi", "pt"],
        "body": "⚠️ WEATHER ALERT for {{1}}: {{2}} expected in the next {{3}} hours. Recommendation: {{4}}. Reply 1 for action plan or 0 to dismiss.",
        "parameters_example": ["Free State", "Frost warning", "12", "Delay sensitive planting and irrigate"],
    },
    {
        "name": "krishinet_outbreak_warning_v1",
        "category": "UTILITY",
        "languages": ["en", "hi", "pt"],
        "body": "🚨 PEST/DISEASE OUTBREAK ALERT: {{1}} detected in {{2}} district with {{3}} severity. Immediate action: {{4}}. Reply 2 to diagnose your crop.",
        "parameters_example": ["Fall Armyworm", "Cascavel", "HIGH", "Scout field borders and prepare pheromone traps"],
    },
]
