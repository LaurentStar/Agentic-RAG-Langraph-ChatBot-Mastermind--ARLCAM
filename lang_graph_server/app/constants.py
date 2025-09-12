from enum import Enum, IntEnum

class AnnouncementStates(str,Enum):
    RETRIEVE = "retrieve"
    GRADE_DOCUMENTS = "grade_documents"
    GENERATE = "generate"
    WEBSEARCH = "websearch"
    BROADCAST_NORMAL = 'broadcast_normal'

class BotActions(str, Enum):
    DETERMINE_IF_CHAT_MESSAGE_OR_ANNOUNCEMENT = 'determine_if_chat_message_or_annoncement'
    DECIDE_TO_RESPONSE = 'decide_to_response'

class Tone(str,Enum):
    ANGRY = 'angry'
    ANXIOUS = 'anxious'
    BITTER = 'bitter'
    CRITICAL = 'critical'
    ESSIMISTIC = 'essimistic'
    EXCITED = 'excited'
    FOREBODING = 'foreboding'
    HAPPY = 'happy'
    SAD = 'sad'
    TENSE = 'tense'
    UNSURE = 'unsure'
    NOT_WITHIN_SCOPE = 'not_within_scope'


