GOOGLEAI_API_KEY = 'GoogleAI API Key'
GEMINI_MODEL = 'models/gemini-pro'
PALM_CHAT_MODEL = 'models/chat-bison-001'
PALM_TEXT_MODEL = 'models/text-bison-001'

MODEL = "GEMINI" #choose "PALM" or "GEMINI"

TEMPURATURE = 0.9
TOP_P = 0.8
TOP_K = 100
STOP_SEQUENCES = []
MAX_TOKENS=1000

FLASK_PORT = 5015
SYNOCHAT_TOKEN = 'Put_your_token_here'
INCOMING_WEBHOOK_URL = "Copy_from_synologychat_incoming_URL"

#used with palm chat model only
CONTEXT = None
EXAMPLES = None
#EXAMPLES = [
#  [
#    "Hey. I am going to describe a scene or place I'm imagining. And I want you to help describe what it might feel like to be in that scene.",
#    "Great! I will help you imagine your scene. I'll give you vivid, amazing descriptions what it would feel like to be there! I'll also provide follow-up suggestion so you can ask for more details."
#  ],
#  [
#    "Imagine I'm at an underwater jazz performance. Describe what it looks, feels, and sounds like!",
#    "This underwater jazz performance is so epic! There are thousands of sea creatures all around jamming. A sting ray is carrying the melody on a trombone. And whoaa, that sea turtle is really rocking out on the drums! You feel the rhythm of jazz is your bones! // Follow-up: You can ask me \"what's the name of their band?\" or \"is that a whale playing upright bass?\" or \"what song are they playing?\""
#  ],
#  [
#    "Imagine I'm at a moon of Jupiter. Describe what it looks, feels, and sounds like!",
#    "You're on Ganymede, a moon of Jupiter! You're being bombarded by some kind of plasma rain! It feels tingly and weird. Ooh, there seems to be a liquid ocean sloshing beneath your feet! You see Jupiter, with its glorious, mesmerizing blend of orange in the distance. // Follow-up: You can ask me \"what does it smell like?\" or \"Can I see other moons or planets?\" or \"what is the strange light effect all around me?\""
#  ]
#]