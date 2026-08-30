import json
import os

LANGUAGES = {
    "as": {"name": "Assamese", "flood": "বানপানী সতর্কতা", "cyclone": "ঘূর্ণিঝড় সতর্কতা", "landslide": "ভূমিস্খলন সতর্কতা", "wildfire": "দাবানল সতর্কতা", "earthquake": "ভূমিকম্প সতর্কতা", "tsunami": "চুনামী সতর্কতা", "heatwave": "গৰম বতাহ সতর্কতা", "evacuate": "অবিলম্বে {destination} লৈ খালী কৰক", "call": "112 কল কৰক"},
    "bn": {"name": "Bengali", "flood": "বন্যা সতর্কতা", "cyclone": "ঘূর্ণিঝড় সতর্কতা", "landslide": "ধস সতর্কতা", "wildfire": "দাবানল সতর্কতা", "earthquake": "ভূমিকম্প সতর্কতা", "tsunami": "সুনামি সতর্কতা", "heatwave": "তীব্র তাপ্রবাহ সতর্কতা", "evacuate": "অবিলম্বে {destination} এ চলে যান", "call": "112 এ কল করুন"},
    "brx": {"name": "Bodo", "flood": "दैबाना सांग्राংथि", "cyclone": "बारहुंखा सांग्राংथि", "landslide": "হা खोख्रेना सांग्राংथि", "wildfire": "हाग्रामा अर सांग्राংथि", "earthquake": "बांलु सांग्राংथि", "tsunami": "सुनामी सांग्राংथि", "heatwave": "गुदुं बार सांग्राংथि", "evacuate": "गोख्रै {destination} आव थां", "call": "112 आव कल खालाम"},
    "doi": {"name": "Dogri", "flood": "बाढ़ चेतावनी", "cyclone": "चक्रवात चेतावनी", "landslide": "भूस्खलन चेतावनी", "wildfire": "जंगल दी अग्गी दी चेतावनी", "earthquake": "भुचाल चेतावनी", "tsunami": "सुनामी चेतावनी", "heatwave": "लू दी चेतावनी", "evacuate": "झटपट {destination} गी निकलो", "call": "112 पर काल करो"},
    "gu": {"name": "Gujarati", "flood": "પૂર ચેતવણી", "cyclone": "વાવાઝોડું ચેતવણી", "landslide": "ભૂસ્ખલન ચેતવણી", "wildfire": "દાવાનળ ચેતવણી", "earthquake": "ભૂકંપ ચેતવણી", "tsunami": "સુનામી ચેતવણી", "heatwave": "લૂ ચેતવણી", "evacuate": "તાત્કાલિક {destination} તરફ ખસી જાઓ", "call": "112 પર કોલ કરો"},
    "hi": {"name": "Hindi", "flood": "बाढ़ चेतावनी", "cyclone": "चक्रवात चेतावनी", "landslide": "भूस्खलन चेतावनी", "wildfire": "दावानल चेतावनी", "earthquake": "भूकंप चेतावनी", "tsunami": "सुनामी चेतावनी", "heatwave": "लू चेतावनी", "evacuate": "तुरंत {destination} की ओर प्रस्थान करें", "call": "112 पर कॉल करें"},
    "kn": {"name": "Kannada", "flood": "ಪ್ರವಾಹ ಮುನ್ನೆಚ್ಚರಿಕೆ", "cyclone": "ಚಂಡಮಾರುತ ಮುನ್ನೆಚ್ಚರಿಕೆ", "landslide": "ಭೂಕುಸಿತ ಮುನ್ನೆಚ್ಚರಿಕೆ", "wildfire": "ಕಾಡ್ಗಿಚ್ಚು ಮುನ್ನೆಚ್ಚರಿಕೆ", "earthquake": "ಭೂಕಂಪ ಮುನ್ನೆಚ್ಚರಿಕೆ", "tsunami": "ಸುನಾಮಿ ಮುನ್ನೆಚ್ಚರಿಕೆ", "heatwave": "ಬಿಸಿಗಾಳಿ ಮುನ್ನೆಚ್ಚರಿಕೆ", "evacuate": "ತಕ್ಷಣ {destination} ಗೆ ಸ್ಥಳಾಂತರಗೊಳ್ಳಿ", "call": "112 ಗೆ ಕರೆ ಮಾಡಿ"},
    "ks": {"name": "Kashmiri", "flood": "سیلاب ہوشیار", "cyclone": "طوفان ہوشیار", "landslide": "پہاڑ پھٹنے کی وارننگ", "wildfire": "جنگلی آگ ہوشیار", "earthquake": "بھونچال ہوشیار", "tsunami": "سونا می ہوشیار", "heatwave": "لو ہوشیار", "evacuate": "فوری طور پٹہ {destination} گژھیو", "call": "112 کریو فون"},
    "kok": {"name": "Konkani", "flood": "हुंवार शिटकावणी", "cyclone": "वादळ शिटकावणी", "landslide": "माती कोसळप शिटकावणी", "wildfire": "रान पेटप शिटकावणी", "earthquake": "भूंयकांप शिटकावणी", "tsunami": "सुनामी शिटकावणी", "heatwave": "गळम शिटकावणी", "evacuate": "रोखडेच {destination} वचात", "call": "112 फोन करा"},
    "mai": {"name": "Maithili", "flood": "बाढ़ि चेतावनी", "cyclone": "तुफान चेतावनी", "landslide": "भूस्खलन चेतावनी", "wildfire": "वनक आगि चेतावनी", "earthquake": "भूकंप चेतावनी", "tsunami": "सुनामी चेतावनी", "heatwave": "लूक चेतावनी", "evacuate": "तुरंत {destination} चलि जाउ", "call": "112 पर कॉल करू"},
    "ml": {"name": "Malayalam", "flood": "പ്രളയ മുന്നറിയിപ്പ്", "cyclone": "ചുഴലിക്കാറ്റ് മുന്നറിയിപ്പ്", "landslide": "ഉരുൾപൊട്ടൽ മുന്നറിയിപ്പ്", "wildfire": "കാട്ടുതീ മുന്നറിയിപ്പ്", "earthquake": "ഭൂകമ്പ മുന്നറിയിപ്പ്", "tsunami": "സുനാമി മുന്നറിയിപ്പ്", "heatwave": "ഉഷ്ണതരംഗ മുന്നറിയിപ്പ്", "evacuate": "ഉടനടി {destination} ലേക്ക് മാറുക", "call": "112 ലേക്ക് വിളിക്കുക"},
    "mni": {"name": "Manipuri", "flood": "ঈশিং ইচাও চেকশিল থৌরাং", "cyclone": "নুংশিৎ সিৎপা চেকশিল থৌরাং", "landslide": "চিং মায় খাইনবা চেকশিল থৌরাং", "wildfire": "উমং মৈ চাউবা চেকশিল থৌরাং", "earthquake": "লৈবাক নিংবা চেকশিল থৌরাং", "tsunami": "সুনামি চেকশিল থৌরাং", "heatwave": "অশা চাউবা চেকশিল থৌরাং", "evacuate": "থুনা {destination} দা ফিশাফম লৌখিনু", "call": "112 দা ফোল থৌ"},
    "mr": {"name": "Marathi", "flood": "पूर इशारा", "cyclone": "वादळ इशारा", "landslide": "दरड कोसळणे इशारा", "wildfire": "दावानल इशारा", "earthquake": "भूकंप इशारा", "tsunami": "सुनामी इशारा", "heatwave": "अतिउष्णता इशारा", "evacuate": "ताबडतोब {destination} कडे स्थलांतरित व्हा", "call": "112 वर कॉल करा"},
    "ne": {"name": "Nepali", "flood": "बाढी चेतावनी", "cyclone": "चक्रवात चेतावनी", "landslide": "पहिरो चेतावनी", "wildfire": "डढेलो चेतावनी", "earthquake": "भूकम्प चेतावनी", "tsunami": "सुनामी चेतावनी", "heatwave": "लू चेतावनी", "evacuate": "तुरन्त {destination} तर्फ जानुहोस्", "call": "112 मा कल गर्नुहोस्"},
    "or": {"name": "Odia", "flood": "ବନ୍ୟା ସତର୍କତା", "cyclone": "ବାତ୍ୟା ସତର୍କତା", "landslide": "ଭୂସ୍ଖଳନ ସତର୍କତା", "wildfire": "ଦାବାନଳ ସତର୍କତା", "earthquake": "ଭୂକମ୍ପ ସତର୍କତା", "tsunami": "ସୁନାମି ସତର୍କତା", "heatwave": "ଅଂଶୁଘାତ ସତର୍କତା", "evacuate": "ତୁରନ୍ତ {destination} କୁ ଚାଲିଯାଆନ୍ତୁ", "call": "112 କୁ କଲ୍ କରନ୍ତୁ"},
    "pa": {"name": "Punjabi", "flood": "ਹੜ੍ਹ ਦੀ ਚੇਤਾਵਨੀ", "cyclone": "ਚੱਕਰਵਾਤ ਚੇਤਾਵਨੀ", "landslide": "ਜ਼ਮੀਨ ਖਿਸਕਣ ਦੀ ਚੇਤਾਵਨੀ", "wildfire": "ਜੰਗਲ ਦੀ ਅੱਗ ਦੀ ਚੇਤਾਵਨੀ", "earthquake": "ਭੂਚਾਲ ਦੀ ਚੇਤਾਵਨੀ", "tsunami": "ਸੁਨਾਮੀ ਚੇਤਾਵਨੀ", "heatwave": "ਲੂ ਦੀ ਚੇਤਾਵਨੀ", "evacuate": "ਤੁਰੰਤ {destination} ਵੱਲ ਜਾਓ", "call": "112 'ਤੇ ਕਾਲ ਕਰੋ"},
    "sa": {"name": "Sanskrit", "flood": "जलौघः चेतावनी", "cyclone": "चक्रवातः चेतावनी", "landslide": "भूसङ्क्रमणम् चेतावनी", "wildfire": "वनाग्निः चेतावनी", "earthquake": "भूकम्पः चेतावनी", "tsunami": "सुनामी चेतावनी", "heatwave": "ऊष्णलहरी चेतावनी", "evacuate": "शीघ्रं {destination} गच्छन्तु", "call": "112 इति दूरभाषं कुर्वन्तु"},
    "sat": {"name": "Santali", "flood": "ᱫᱟᱜ ᱵᱟᱰ ᱦᱚᱥᱤᱭᱟᱹᱨ", "cyclone": "ᱦᱚᱭ ᱵᱟᱹᱨᱰᱩ ᱦᱚᱥᱤᱭᱟᱹᱨ", "landslide": "ᱦᱟᱥᱟ ᱫᱷᱟᱥᱟᱣ ᱦᱚᱥᱤᱭᱟᱹᱨ", "wildfire": "ᱵᱤᱨ ᱥᱮᱸᱜᱮᱞ ᱦᱚᱥᱤᱭᱟᱹᱨ", "earthquake": "ᱚᱛ ᱞᱟᱲᱟᱣ ᱦᱚᱥᱤᱭᱟᱹᱨ", "tsunami": "ᱥᱩᱱᱟᱢᱤ ᱦᱚᱥᱤᱭᱟᱹᱨ", "heatwave": "ᱞᱚᱞᱚ ᱦᱚᱭ ᱦᱚᱥᱤᱭᱟᱹᱨ", "evacuate": "ᱞᱚᱜᱚᱱ {destination} ᱛᱮ ᱥᱮᱱᱚᱜ ᱯᱮ", "call": "112 ᱛᱮ ᱯᱷᱳᱱ ᱢᱮ"},
    "sd": {"name": "Sindhi", "flood": "ٻوڏ جي دانهن", "cyclone": "طوفان جي دانهن", "landslide": "مٽي ڪرڻ جي دانهن", "wildfire": "جنگل جي باهه جي دانهن", "earthquake": "زلزلي جي دانهن", "tsunami": "سنامي جي دانهن", "heatwave": "لوهه جي دانهن", "evacuate": "جلد ئي {destination} ڏانهن نڪرو", "call": "112 تي ڪال ڪريو"},
    "ta": {"name": "Tamil", "flood": "வெள்ள எச்சரிக்கை", "cyclone": "புயல் எச்சரிக்கை", "landslide": "நிலச்சரிவு எச்சரிக்கை", "wildfire": "காட்டுத்தீ எச்சரிக்கை", "earthquake": "நிலநடுக்க எச்சரிக்கை", "tsunami": "சுனாமி எச்சரிக்கை", "heatwave": "வெப்ப அலை எச்சரிக்கை", "evacuate": "உடனடியாக {destination} க்கு வெளியேறவும்", "call": "112 ஐ அழைக்கவும்"},
    "te": {"name": "Telugu", "flood": "వరద హెచ్చరిక", "cyclone": "తుఫాను హెచ్చరిక", "landslide": "భూపాత హెచ్చరిక", "wildfire": "దావానలం హెచ్చరిక", "earthquake": "భూకంపం హెచ్చరిక", "tsunami": "సునామీ హెచ్చరిక", "heatwave": "వడగాల్పుల హెచ్చరిక", "evacuate": "వెంటనే {destination} కి వెళ్ళండి", "call": "112 కి కాల్ చేయండి"},
    "ur": {"name": "Urdu", "flood": "سیلاب کی وارننگ", "cyclone": "طوفان کی وارننگ", "landslide": "لینڈ سلائیڈ کی وارننگ", "wildfire": "جنگل کی آگ کی وارننگ", "earthquake": "زلزلہ کی وارننگ", "tsunami": "سنامی کی وارننگ", "heatwave": "لو کی وارننگ", "evacuate": "فوری طور پر {destination} منتقل ہو جائیں", "call": "112 پر کال کریں"}
}

HAZARD_MAP = {
    "F": "flood",
    "C": "cyclone",
    "L": "landslide",
    "W": "wildfire",
    "E": "earthquake",
    "T": "tsunami",
    "H": "heatwave"
}

data_dir = os.path.dirname(os.path.abspath(__file__))

# Read templates_en.json as basis for structures
with open(os.path.join(data_dir, "templates_en.json"), encoding="utf-8") as f:
    basis = json.load(f)

for code, details in LANGUAGES.items():
    output_templates = {}
    for hz_code, hz_key in HAZARD_MAP.items():
        base_h = basis[hz_code]
        title_local = details[hz_key]
        evac_local = details["evacuate"]
        call_local = details["call"]
        
        output_templates[hz_code] = {
            "title": title_local,
            "tier1_general": f"⚠️ {title_local} — {{area}}: {evac_local}. Avoid danger zones.",
            "tier1_agricultural": f"⚠️ {title_local} — {details['name']} Farmers: Protect crops/livestock. {evac_local}.",
            "tier1_elderly": f"⚠️ {title_local} — {details['name']} Seniors: Contact authorities. {evac_local}.",
            "tier1_physically_challenged": f"⚠️ {title_local} — {details['name']} Accessibility Support Active. {evac_local}. {call_local}.",
            "tier1_volunteers": f"⚠️ {title_local} — {details['name']} Responders: Mobilize immediately to {{destination}}.",
            "tier2_prompt": base_h["tier2_prompt"],  # Prompts are built using English instructions for SLM grounding
            "fallback": f"⚠️ {title_local} — {{area}}: {evac_local}. {call_local}."
        }
        
    out_path = os.path.join(data_dir, f"templates_{code}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_templates, f, ensure_ascii=False, indent=2)

print(f"Generated templates for {len(LANGUAGES)} languages.")
