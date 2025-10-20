from enum import Enum, IntEnum
from pydantic import BaseModel, Field

#-------#
# ENUMS #
#-------#

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
    AMUSED = 'amused'           ; ANGRY = 'angry'           ; ANXIOUS = 'anxious'       ; ACCUSATORY = 'accusatory'
    AGGRESSIVE = 'aggressive'   ; APOLOGETIC = 'apologetic' ; APATHETIC = 'apathetic'   ; ASSERTIVE = 'assertive'
    BITTER = 'bitter'           ; BOLD = 'bold'             ; BOORISH = 'boorish'       ; BEWILDERED = 'bewildered'
    CALM = 'calm'               ; CRITICAL = 'critical'     ; CHEERFUL = 'cheerful'     ; CONFUSED = 'confused'
    ESSIMISTIC = 'essimistic'   ; EXCITED = 'excited'
    FORMAL='formal'             ; FOREBODING = 'foreboding'
    HAPPY = 'happy'
    SAD = 'sad'                 ; SEDUCTIVE = 'seductive'
    TENDER='tender'             ; TENSE = 'tense'
    UNSURE = 'unsure'
    NOT_WITHIN_SCOPE = 'not_within_scope'

class SocialMediaPlatform(str,Enum):
    TWITTER = 'twitter'
    DISCORD = 'discord'  
    SLACK = 'slack'
    FACEBOOK = 'facebook'
    BLUESKY = 'bluesky'
    EMAIL = 'email'
    DEFUALT = 'defualt'

class PromptFileExtension(str, Enum):
    MARKDOWN = ".md"

class AllowedUploadFileTypes(str, Enum):
    CSV = '.csv'
    EXCEL = '.xlsx'


class Node(str, Enum):
    INITIALIZATION = 'initialization'

#----------------------------------------#
# BUILDING BLOCK STUCTURED OUTPUT MODELS #
#----------------------------------------#
class UnitBall_SO(BaseModel):
    unit_ball_score : float = Field(
        description="A score that goes from -1 to 1. It is the closest universal representation of this range I could find within 10 seconds of research.",
        ge=-1.0, le=1.0
    )

class IO_SO(BaseModel):
    io : bool = Field(description="A value of true or false. This represent a decision from the llm ")