from enum import Enum

class CardType(Enum):
    DUKE = 'duke'
    ASSASSIN = 'assassin'  
    CAPTAIN = 'captain'
    AMBASSADOR = 'ambassador'
    COURTESSA = 'countessa'
    DEFUALT = 'defualt'

class SocailMediaPlatform(Enum):
    TWITTER = 'twitter'
    DISCORD = 'discord'  
    SLACK = 'slack'
    FACEBOOK = 'facebook'
    BLUESKY = 'bluesky'
    EMAIL = 'email'
    DEFUALT = 'defualt'

class PlayerStatus(Enum):
    DEAD = 'dead'
    ALIVE = 'alivecl'  
    HIDDEN = 'hidden'
    WAITING = 'waiting'
    DISABLED = 'disabled'
    ENPOWERED = 'empowered'
    CLAIRAUDIENT = 'clairaudient'

