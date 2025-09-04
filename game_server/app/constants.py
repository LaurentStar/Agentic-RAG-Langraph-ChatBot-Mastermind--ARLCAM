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
    ACT_FOREIGN_AID = 'act_foreign_aid'
    ACT_COUP = 'act_coup'
    ACT_STEAL = 'act_steal'
    ACT_BLOCK = 'act_block'
    ACT_SWAP_INFLUENCE = 'act_swap_influence'

    OCCURENCE_ASSASSINATED = 'occurance_assassinated'

    NO_EVENT = 'no_event'



class SpecialAbilityCost(IntEnum):
    COUP = 7
    ASSASSINATE = 3
    ASSASSINATE_UPGRADE = 2
    STEAL = 0
    STEAL_UPGRADE = 1
    SWAP_INFLUENCE = 0
    SWAP_INFLUENCE_UPGRADE = 4

    


