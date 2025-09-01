from enum import Enum, IntEnum

class CardType(str,Enum):
    DUKE = 'duke'
    ASSASSIN = 'assassin'  
    CAPTAIN = 'captain'
    AMBASSADOR = 'ambassador'
    COURTESSA = 'countessa'
    DEFUALT = 'defualt'

class SocialMediaPlatform(str,Enum):
    TWITTER = 'twitter'
    DISCORD = 'discord'  
    SLACK = 'slack'
    FACEBOOK = 'facebook'
    BLUESKY = 'bluesky'
    EMAIL = 'email'
    DEFUALT = 'defualt'

class PlayerStatus(str,Enum):
    DEAD = 'dead'
    ALIVE = 'alive'  
    ACTING = 'acting'
    HIDDEN = 'hidden'
    WAITING = 'waiting'
    DISABLED = 'disabled'
    ENPOWERED = 'empowered'
    CLAIRAUDIENT = 'clairaudient'

class ToBeInitiated(str,Enum):
    ACT_ASSASSINATION = 'act_assassination'
    OCCURENCE_ASSASSINATED = 'occurance_assassinated'
    NO_EVENT = 'no_event'



class SpecialAbilityCost(IntEnum):
    ASSASSINATE = 3
    ASSASSINATE_UPGRADE = 2


